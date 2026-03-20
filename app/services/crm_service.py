from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from app.config import get_app_settings
from app.db import (
    add_customer_memory_note,
    add_customer_memory_fact,
    add_customer_memory_suggestion,
    add_conversation_checkpoint,
    add_audit_event,
    add_turn,
    bump_session_state_versions,
    ensure_session,
    find_related_session_ids,
    get_conversation_checkpoints,
    get_connection,
    get_customer_memory_facts,
    get_customer_memory_notes,
    get_customer_memory_suggestions,
    get_recent_turn_summaries,
    get_session_state,
    row_to_dict,
    update_customer_memory_fact_status,
    update_memory_suggestion_status,
    update_session_state,
)
from app.services.access_control import RequestActor
from app.schemas import ActionMutationResponse, CRMAction, CRMChatResponse, CRMComponent, CRMMessage, EntityDetailResponse, TaskCompleteResponse
from app.services.agent_memory import (
    build_customer_lookup,
    detect_memory_conflict,
    extract_memory_facts,
    extract_memory_note_update,
    extract_memory_suggestion,
    extract_preference_signals,
    get_customer_memory_bundle,
    get_layered_memory_bundle,
    is_memory_update_request,
    is_relationship_maintenance_request,
    resolve_turn_context,
)
from app.services.guardrails import evaluate_message
from app.services.knowledge_service import retrieve_knowledge_briefs
from app.services.llm_adapter import generate_assistant_brief, generate_message_draft
from app.services.workflow_service import resolve_workflow


SUPPORTED_ACTIONS = [
    "open_customer",
    "open_product",
    "open_task",
    "complete_task",
    "open_session",
    "approve_memory_suggestion",
    "reject_memory_suggestion",
]
CONTEXT_VERSION = "crm-v2-memory"
RESPONSE_CACHE: dict[tuple[str, str, str], CRMChatResponse] = {}


def _invalidate_cache_for_sessions(session_ids: list[str]) -> None:
    if not session_ids:
        return
    target_sessions = set(session_ids)
    stale_keys = [key for key in RESPONSE_CACHE if key[0] in target_sessions]
    for key in stale_keys:
        RESPONSE_CACHE.pop(key, None)


def _serialize_session_snapshot(state: dict) -> dict:
    return {
        "active_customer_id": state.get("active_customer_id") or "",
        "active_customer_name": state.get("active_customer_name") or "",
        "active_intent": state.get("active_intent") or "",
        "conversation_mode": state.get("conversation_mode") or "",
        "last_response_shape": state.get("last_response_shape") or "",
        "last_entity_ids": state.get("last_entity_ids") or [],
        "handoff_reason": state.get("handoff_reason") or "",
        "state_version": int(state.get("state_version") or 0),
        "working_memory_summary": state.get("working_memory_summary") or "",
    }


def _build_mutation_session_meta(connection, session_ids: list[str]) -> dict:
    if not session_ids:
        return {}
    session_id = session_ids[0]
    state = get_session_state(connection, session_id)
    return {
        "session_id": session_id,
        "state_version": int(state.get("state_version") or 0),
        "session_snapshot": _serialize_session_snapshot(state),
    }


QUESTION_TYPE_TO_RESPONSE_SHAPE = {
    "customer_overview": "customer_overview+workflow_checkpoint+customer_list",
    "customer_filter": "workflow_checkpoint+customer_list",
    "customer_constraint_filter": "workflow_checkpoint+customer_list",
    "customer_insight": "customer_spotlight+detail_kv+tag_group+memory_briefs",
    "customer_preference_validation": "customer_spotlight+detail_kv+tag_group+memory_briefs",
    "product_recommendation": "product_grid",
    "customer_product_recommendation": "customer_spotlight+workflow_checkpoint+product_grid",
    "relationship_maintenance": "customer_spotlight+workflow_checkpoint+relationship_plan+knowledge_briefs+product_grid",
    "message_draft": "customer_spotlight+workflow_checkpoint+optional_product_grid+message_draft",
    "category_inventory": "category_overview",
    "customer_tag_inventory": "tag_group",
    "task_management": "task_list",
    "task_management_with_trace": "workflow_checkpoint+task_list",
    "clarification": "clarification_notice",
    "rejection": "safety_notice",
}

QUESTION_TYPE_TO_CONVERSATION_MODE = {
    "customer_overview": "customer_overview",
    "customer_filter": "customer_screening",
    "customer_constraint_filter": "customer_screening",
    "customer_insight": "customer_insight",
    "customer_preference_validation": "customer_insight",
    "product_recommendation": "product_recommendation",
    "customer_product_recommendation": "product_recommendation",
    "relationship_maintenance": "relationship_maintenance",
    "message_draft": "message_draft",
    "category_inventory": "inventory_overview",
    "customer_tag_inventory": "customer_insight",
    "task_management": "task_management",
    "task_management_with_trace": "task_management",
    "clarification": "clarification",
    "rejection": "safety",
}

CONVERSATION_MODE_LABELS = {
    "customer_overview": "看客户池",
    "customer_screening": "筛优先客户",
    "customer_insight": "看客户画像",
    "product_recommendation": "看商品推荐",
    "relationship_maintenance": "整理维护方式",
    "message_draft": "整理沟通方式",
    "inventory_overview": "看门店范围",
    "task_management": "处理待办任务",
    "clarification": "补充一下关键信息",
    "safety": "边界保护",
}

REPEAT_QUERY_DIVERSIFY_CUES = {
    "换一批",
    "换几个",
    "再来几件",
    "再来几款",
    "还有别的",
    "看看别的",
    "换点别的",
    "重新推荐",
}


@dataclass(frozen=True)
class ChatDecision:
    question_type: str
    response_shape: str
    context_resolution: dict


def get_bootstrap_payload() -> dict:
    settings = get_app_settings()
    with get_connection() as connection:
        pending = connection.execute(
            "SELECT COUNT(*) FROM follow_up_tasks WHERE status = 'open'"
        ).fetchone()[0]
    return {
        "advisor_id": settings.advisor_id,
        "advisor_name": settings.advisor_name,
        "store_id": settings.store_id,
        "store_name": settings.store_name,
        "brand_name": settings.brand_name,
        "pending_task_count": pending,
        "quick_prompts": list(settings.quick_prompts),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_message(message: str) -> str:
    return " ".join(message.split()).strip().lower()


def _tier_weight(tier: str) -> int:
    return {"黑金": 4, "高潜": 3, "重点": 2, "稳定": 1}.get(tier, 0)


def _priority_weight(priority: str) -> int:
    return {"高": 3, "中": 2, "低": 1}.get(priority, 0)


def _fetch_customer_tags(connection, customer_id: str) -> list[str]:
    rows = connection.execute(
        "SELECT tag FROM customer_tags WHERE customer_id = ? ORDER BY importance ASC",
        (customer_id,),
    ).fetchall()
    return [row["tag"] for row in rows]


def _fetch_product_names(connection, product_ids: list[str]) -> list[str]:
    if not product_ids:
        return []
    placeholders = ",".join("?" for _ in product_ids)
    rows = connection.execute(
        f"SELECT name FROM products WHERE id IN ({placeholders})",
        tuple(product_ids),
    ).fetchall()
    return [row["name"] for row in rows]


def _fetch_customer_name_map(connection, customer_ids: list[str]) -> dict[str, str]:
    return build_customer_lookup(connection, customer_ids)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _dedupe_products(items: list[dict], limit: int) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in items:
        signature = "|".join(
            [
                str(item.get("name", "")).strip(),
                str(item.get("color", "")).strip(),
                str(item.get("category", "")).strip(),
            ]
        )
        if not signature or signature in seen:
            continue
        seen.add(signature)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


def _compact_assistant_summary(text: str, fallback_text: str) -> str:
    cleaned = " ".join(text.replace("\n", " ").split()).strip()
    if not cleaned:
        cleaned = fallback_text

    segments = [
        segment.strip(" ，。；")
        for segment in cleaned.replace("！", "。").replace("？", "。").split("。")
        if segment.strip(" ，。；")
    ]
    if not segments:
        compact = " ".join(fallback_text.replace("\n", " ").split()).strip()
        return compact[:72]

    compact = "。 ".join(segments[:2]).strip()
    if len(compact) > 72:
        compact = compact[:72].rstrip("，；、 ") + "…"
    elif not compact.endswith(("。", "！", "？", "…")):
        compact += "。"
    return compact


def _find_named_customer_ids(connection, message: str, limit: int = 1) -> list[str]:
    rows = connection.execute(
        """
        SELECT id, name, lifetime_value, last_contact_at
        FROM customers
        ORDER BY lifetime_value DESC, last_contact_at DESC
        """
    ).fetchall()
    matches = [dict(row) for row in rows if row["name"] and str(row["name"]) in message]
    matches.sort(key=lambda item: (item["lifetime_value"], item["last_contact_at"]), reverse=True)
    return [str(item["id"]) for item in matches[:limit]]


def _query_customer_candidates(
    connection,
    message: str,
    limit: int,
    customer_ids: list[str] | None = None,
    exclude_ids: list[str] | None = None,
) -> list[dict]:
    base_query = """
        SELECT c.*, MIN(t.due_date) AS due_date, MAX(t.priority) AS task_priority, t.id AS task_id
        FROM customers c
        LEFT JOIN follow_up_tasks t
          ON c.id = t.customer_id AND t.status = 'open'
    """
    params: tuple[str, ...] = ()
    if customer_ids:
        placeholders = ",".join("?" for _ in customer_ids)
        base_query += f" WHERE c.id IN ({placeholders})"
        params = tuple(customer_ids)
    base_query += " GROUP BY c.id"

    rows = connection.execute(base_query, params).fetchall()
    ranked = []
    for row in rows:
        customer = dict(row)
        if exclude_ids and customer["id"] in exclude_ids:
            continue
        tags = _fetch_customer_tags(connection, customer["id"])
        score = customer["lifetime_value"] // 800 + _tier_weight(customer["tier"]) * 2
        if "高净值" in message and "高净值" in tags:
            score += 6
        if "今天" in message or "今日" in message:
            if customer["due_date"]:
                score += 4
        if "未联系" in message or "没联系" in message or "未触达" in message:
            score += 3
        if "西装" in message and "西装" in json.loads(customer["preferred_categories"]):
            score += 5
        ranked.append((score, customer, tags))

    ranked.sort(key=lambda item: (item[0], item[1]["lifetime_value"]), reverse=True)
    candidates = []
    for _, customer, tags in ranked[:limit]:
        next_action = "先发私聊，再补一条今日跟进记录。"
        reason = f"客单累计 {customer['lifetime_value']}，标签包含 {'、'.join(tags[:2])}。"
        candidates.append(
            {
                "id": customer["id"],
                "name": customer["name"],
                "tier": customer["tier"],
                "profile": customer["style_profile"],
                "style_profile": customer["style_profile"],
                "preferred_categories": customer["preferred_categories"],
                "preferred_colors": customer["preferred_colors"],
                "tags": tags,
                "reason": reason,
                "next_action": next_action,
                "task_id": customer["task_id"],
            }
        )
    return candidates


def _query_products(
    connection,
    message: str,
    limit: int,
    *,
    category_hint: str = "",
    season_hint: str = "",
    query_terms: list[str] | None = None,
    focus_customer: dict | None = None,
    memory_preferences: dict | None = None,
    exclude_ids: list[str] | None = None,
) -> list[dict]:
    rows = connection.execute(
        """
        SELECT p.*, i.availability, i.store_stock, i.warehouse_stock
        FROM products p
        JOIN inventory i ON i.product_id = p.id
        WHERE i.store_stock > 0
        """
    ).fetchall()

    terms = [term for term in (query_terms or []) if term]
    ranked: list[tuple[int, dict]] = []
    for row in rows:
        product = dict(row)
        if exclude_ids and product["id"] in exclude_ids:
            continue
        style_tags = json.loads(product["style_tags"])
        preferred_categories = (
            set(json.loads(str(focus_customer["preferred_categories"])))
            if focus_customer and focus_customer.get("preferred_categories")
            else set()
        )
        preferred_colors = (
            set(json.loads(str(focus_customer["preferred_colors"])))
            if focus_customer and focus_customer.get("preferred_colors")
            else set()
        )
        focus_profile = str(focus_customer.get("style_profile", "")) if focus_customer else ""
        haystack = " ".join(
            [
                product["name"],
                product["category"],
                product["subcategory"],
                product["collection_name"],
                product["summary"],
                product["color"],
                " ".join(style_tags),
            ]
        )

        score = product["store_stock"] * 2 + product["warehouse_stock"]
        reason_bits: list[str] = []
        matched_terms: list[str] = []
        if focus_customer:
            if product["category"] in preferred_categories:
                score += 16
                reason_bits.append(f"命中 {focus_customer['name']} 常买的 {product['category']} 品类")
            if product["color"] in preferred_colors:
                score += 10
                reason_bits.append(f"颜色更接近 {focus_customer['name']} 的偏好")
            if focus_profile and any(token in haystack for token in focus_profile.split()):
                score += 8

        if memory_preferences:
            negative_categories = set(memory_preferences.get("negative_categories", set()))
            negative_colors = set(memory_preferences.get("negative_colors", set()))
            positive_categories = set(memory_preferences.get("positive_categories", set())) - negative_categories
            positive_colors = set(memory_preferences.get("positive_colors", set())) - negative_colors
            if product["category"] in positive_categories:
                score += 14
                reason_bits.append("命中近期补充的品类偏好")
            if product["color"] in positive_colors:
                score += 8
                reason_bits.append("颜色更贴近近期补充偏好")
            if product["category"] in negative_categories:
                score -= 20
                reason_bits.append("已避开客户明确不偏好的品类")
            if product["color"] in negative_colors:
                score -= 12
                reason_bits.append("已避开客户明确不偏好的颜色")

        if category_hint and product["category"] == category_hint:
            score += 18
            reason_bits.append(f"命中你要的 {category_hint} 品类")
        if season_hint and season_hint in {"夏天", "春天"} and "春夏" in product["collection_name"]:
            score += 10
            reason_bits.append(f"属于 {product['collection_name']}，适合 {season_hint} 场景")
        if "夏天" in message and any(token in haystack for token in ["春夏", "轻", "通勤"]):
            score += 8
            reason_bits.append("材质和系列更适合夏季穿着")

        for term in terms:
            if term and term in haystack:
                score += 6
                matched_terms.append(term)

        if "衣服" in message and product["category"] in {"西装", "衬衫", "针织", "风衣", "半裙", "连衣裙", "牛仔", "外套"}:
            score += 4
        if product["store_stock"] > 0:
            reason_bits.append(f"门店现货 {product['store_stock']} 件")
        ranked.append((score, product))

        product["match_terms"] = _dedupe_preserve_order(matched_terms)
        product["display_tags"] = _dedupe_preserve_order([*matched_terms, *style_tags[:2], product["color"]])[:4]
        product["match_reason"] = "；".join(_dedupe_preserve_order(reason_bits)[:3]) or product["summary"]

    ranked.sort(key=lambda item: (item[0], item[1]["price"]), reverse=True)
    items: list[dict] = []
    for _, product in ranked:
        items.append(
            {
                "id": product["id"],
                "name": product["name"],
                "category": product["category"],
                "color": product["color"],
                "price": product["price"],
                "availability": product["availability"],
                "image_url": product["image_url"],
                "summary": product["summary"],
                "match_reason": product["match_reason"],
                "display_tags": product["display_tags"],
                "match_terms": product["match_terms"],
                "store_stock": product["store_stock"],
                "warehouse_stock": product["warehouse_stock"],
            }
        )
    return _dedupe_products(items, limit)


def _query_tasks(connection, limit: int = 5) -> list[dict]:
    rows = connection.execute(
        """
        SELECT t.*, c.name AS customer_name, c.tier AS customer_tier
        FROM follow_up_tasks t
        JOIN customers c ON c.id = t.customer_id
        WHERE t.status = 'open'
        ORDER BY CASE t.priority WHEN '高' THEN 3 WHEN '中' THEN 2 ELSE 1 END DESC, t.due_date ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def _is_customer_inventory_request(message: str) -> bool:
    normalized = message.replace(" ", "")
    return any(token in normalized for token in ["现在有哪些客户", "有哪些客户", "目前有哪些客户", "都有哪些客户"])


def _is_category_inventory_request(message: str) -> bool:
    normalized = message.replace(" ", "")
    return any(token in normalized for token in ["现在有哪些品类", "有哪些品类", "目前有哪些品类", "都有哪些品类", "现在有哪些分类"])


def _is_customer_tag_inventory_request(message: str) -> bool:
    normalized = message.replace(" ", "")
    return any(token in normalized for token in ["客户标签", "会员标签", "有哪些标签", "看看标签", "想看标签"])


def _is_customer_preference_request(message: str) -> bool:
    normalized = message.replace(" ", "")
    return any(token in normalized for token in ["喜欢什么", "偏好", "客户画像", "画像", "适合推荐什么", "适合什么", "客户标签"])


def _is_customer_constraint_filter_request(message: str) -> bool:
    normalized = message.replace(" ", "")
    constraint_tokens = ["不喜欢", "喜欢", "偏好", "更偏", "适合", "通勤", "轻薄", "显瘦"]
    return "客户" in normalized and any(token in normalized for token in constraint_tokens)


def _is_customer_preference_validation_request(message: str) -> bool:
    normalized = message.replace(" ", "")
    return any(token in normalized for token in ["是不是", "对吗", "吗"]) and any(
        token in normalized for token in ["不喜欢", "喜欢", "偏好", "更偏", "最近"]
    )


def _get_customer_pool_overview(connection) -> dict:
    settings = get_app_settings()
    total = connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    tier_rows = connection.execute(
        """
        SELECT tier, COUNT(*) AS count
        FROM customers
        GROUP BY tier
        ORDER BY CASE tier WHEN '黑金' THEN 1 WHEN '高潜' THEN 2 WHEN '重点' THEN 3 ELSE 4 END
        """
    ).fetchall()
    return {
        "total_customers": int(total),
        "tier_breakdown": [{"tier": str(row["tier"]), "count": int(row["count"])} for row in tier_rows],
        "sample_limit": settings.customer_sample_limit,
    }


def _get_customer_tag_overview(connection, limit: int = 10) -> list[str]:
    rows = connection.execute(
        """
        SELECT tag, COUNT(*) AS count
        FROM customer_tags
        GROUP BY tag
        ORDER BY count DESC, tag ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [f"{row['tag']} · {row['count']}位" for row in rows]


def _get_category_overview(connection) -> dict:
    rows = connection.execute(
        """
        SELECT p.category, COUNT(*) AS product_count, SUM(i.store_stock) AS store_stock
        FROM products p
        JOIN inventory i ON i.product_id = p.id
        GROUP BY p.category
        ORDER BY product_count DESC, p.category ASC
        """
    ).fetchall()
    return {
        "total_categories": len(rows),
        "items": [
            {
                "category": str(row["category"]),
                "product_count": int(row["product_count"]),
                "store_stock": int(row["store_stock"] or 0),
            }
            for row in rows
        ],
    }


def _build_trace_components(guardrail, entity_count: int) -> CRMComponent:
    interpretation_bits = [guardrail.intent_label]
    if guardrail.requested_count:
        interpretation_bits.append(f"数量 {guardrail.requested_count}")
    if guardrail.category_hint:
        interpretation_bits.append(f"品类 {guardrail.category_hint}")
    if guardrail.season_hint:
        interpretation_bits.append(f"季节 {guardrail.season_hint}")
    if guardrail.style_terms:
        interpretation_bits.append(f"风格 {'、'.join(guardrail.style_terms[:3])}")

    return CRMComponent(
        component_type="trace_timeline",
        component_id=f"trace-{uuid.uuid4().hex[:8]}",
        title="处理轨迹",
        props={
            "items": [
                {"label": "识别需求范围", "detail": "，".join(interpretation_bits)},
                {"label": "检索门店数据", "detail": f"仅在门店数据库内检索，命中 {entity_count} 条候选记录"},
                {"label": "整理可执行建议", "detail": "输出客户、商品、任务和沟通建议"},
            ]
        },
    )


def _stage_label(workflow_name: str, workflow_stage: str) -> str:
    labels = {
        ("relationship_maintenance", "need_customer"): "先确认客户",
        ("relationship_maintenance", "maintain_with_products"): "先关怀，再带主推",
        ("relationship_maintenance", "maintain_only"): "先关系修复",
        ("product_recommendation", "customer_matched_recommendation"): "按客户偏好推荐",
        ("product_recommendation", "general_recommendation"): "先缩小商品范围",
        ("customer_filter", "candidate_screening"): "先锁定优先客户",
        ("task_management", "task_execution"): "先清高优任务",
        ("message_draft", "compose_message"): "先成稿再执行",
        ("inventory_lookup", "inventory_check"): "先查库存再推荐",
    }
    return labels.get((workflow_name, workflow_stage), "按当前结果继续推进")


def _build_workflow_checkpoint_component(
    *,
    workflow,
    user_goal: str,
    focus_customer: dict | None,
    products: list[dict],
    tasks: list[dict],
    memory_bundle: dict,
) -> CRMComponent:
    customer_name = focus_customer["name"] if focus_customer else "未锁定客户"
    memory_count = len(memory_bundle.get("memory_notes", []))
    result_summary = f"客户 {1 if focus_customer else 0} · 商品 {len(products)} · 任务 {len(tasks)}"
    notes = [
        workflow.rationale,
        workflow.next_step,
        "仅基于门店内客户、商品、库存与任务数据整理。",
    ]
    if focus_customer and memory_count:
        notes.insert(2, f"已带入 {customer_name} 的 {memory_count} 条长期记录。")

    return CRMComponent(
        component_type="workflow_checkpoint",
        component_id=f"workflow-{uuid.uuid4().hex[:8]}",
        title="本轮执行节奏",
        props={
            "stage_label": _stage_label(workflow.workflow_name, workflow.workflow_stage),
            "workflow_name": workflow.workflow_name,
            "customer_name": customer_name,
            "user_goal": user_goal,
            "result_summary": result_summary,
            "notes": notes[:4],
        },
    )


def _should_include_trace(message: str) -> bool:
    return any(token in message for token in ["为什么", "依据", "怎么判断", "判断逻辑", "处理轨迹"])


def _should_include_message_draft(guardrail, message: str) -> bool:
    return guardrail.intent == "message_draft" or any(token in message for token in ["话术", "私聊", "微信", "怎么说", "文案"])


def _is_pure_memory_update_turn(message: str, memory_note: str | None) -> bool:
    if not memory_note or not is_memory_update_request(message):
        return False
    execution_tokens = ["推荐", "商品", "单品", "衣服", "库存", "任务", "话术", "怎么说", "发什么", "找", "查"]
    return not any(token in message for token in execution_tokens)


def _persist_memory_facts(
    connection,
    *,
    customer_id: str,
    note: str,
    source_type: str,
    source_session_id: str,
    status: str,
    confidence: str,
    confirmed_by: str = "",
) -> None:
    for fact in extract_memory_facts(note):
        add_customer_memory_fact(
            connection,
            customer_id,
            dimension=str(fact["dimension"]),
            value=str(fact["value"]),
            polarity=str(fact["polarity"]),
            qualifier=str(fact.get("qualifier", "")),
            source_type=source_type,
            source_session_id=source_session_id,
            note_source=note,
            status=status,
            confidence=confidence,
            confirmed_by=confirmed_by,
        )


def _format_memory_fact(fact: dict) -> str:
    polarity = "偏好" if str(fact.get("polarity")) == "positive" else "避开"
    value = str(fact.get("value", ""))
    qualifier = str(fact.get("qualifier", ""))
    return f"{polarity} {value}{f' · {qualifier}' if qualifier else ''}".strip()


def _build_relationship_plan_component(
    focus_customer: dict,
    memory_bundle: dict,
    products: list[dict],
    workflow_next_step: str,
) -> CRMComponent:
    customer = memory_bundle.get("customer", {})
    preferred_colors = memory_bundle.get("preferred_colors", [])
    preferred_categories = memory_bundle.get("preferred_categories", [])
    interaction_logs = memory_bundle.get("interaction_logs", [])
    memory_notes = memory_bundle.get("memory_notes", [])
    first_product = products[0]["name"] if products else "当前现货单品"
    second_product = products[1]["name"] if len(products) > 1 else first_product

    strategy_points = [
        f"先从 {customer.get('style_profile', focus_customer.get('profile', '客户偏好'))} 与 {preferred_colors[0] if preferred_colors else '低饱和色'} 切入，降低推销感。",
        f"优先通过 {customer.get('preferred_channel', '微信')} 做轻触达，先问近况与穿着场景，再带出 {first_product}。",
        workflow_next_step or f"如果客户愿意继续聊，再补充 {second_product}，让她在两个明确方向里做选择，不一次推太多。",
    ]
    watchouts = [
        "首轮不要直接堆很多商品参数，先确认她最近的通勤或到店安排。",
        "如果客户回复慢，先用关怀式开场，再顺势带出一件最匹配的现货。",
    ]
    if interaction_logs:
        watchouts[0] = f"结合最近互动：{interaction_logs[0]['summary']}"
    if memory_notes:
        watchouts.append(memory_notes[0]["content"])

    message_seed = (
        f"{focus_customer['name']}，最近帮你留意到两件更贴合你日常穿着的款，"
        f"像 {first_product} 和 {second_product} 都比较适合你一贯偏好的风格，"
        "你这两天如果方便，我可以先把细节发你看看。"
    )

    return CRMComponent(
        component_type="relationship_plan",
        component_id=f"relationship-{uuid.uuid4().hex[:8]}",
        title=f"{focus_customer['name']} 的维护建议",
        props={
            "channel": customer.get("preferred_channel", "微信"),
            "tone": "自然关怀",
            "strategy_points": strategy_points,
            "watchouts": watchouts[:3],
            "message_seed": message_seed,
            "memory_notes": [item["content"] for item in memory_notes[:2]],
            "preferred_summary": f"{focus_customer['profile']} · 偏好 {'、'.join(preferred_categories[:2]) if preferred_categories else '通勤单品'}",
        },
    )


def _build_knowledge_briefs_component(briefs) -> CRMComponent:
    return CRMComponent(
        component_type="knowledge_briefs",
        component_id=f"knowledge-{uuid.uuid4().hex[:8]}",
        title="资深导购经验",
        props={
            "items": [
                {
                    "topic": item.topic,
                    "content": item.content,
                    "source": item.source,
                }
                for item in briefs
            ]
        },
    )


def _build_memory_suggestions_component(focus_customer: dict, items: list[dict]) -> CRMComponent:
    return CRMComponent(
        component_type="memory_suggestions",
        component_id=f"memory-suggestions-{uuid.uuid4().hex[:8]}",
        title=f"{focus_customer['name']} 的待确认记录",
        props={
            "items": [
                {
                    "id": item["id"],
                    "content": item["content"],
                    "note_type": item["note_type"],
                    "confidence": item["confidence"],
                    "source": "本轮观察",
                    "customer_id": focus_customer["id"],
                }
                for item in items
            ]
        },
    )


def _build_clarification_component(title: str, reason: str, prompts: list[str]) -> CRMComponent:
    actions = [
        CRMAction(
            action_type="retry_send",
            label=prompt,
            entity_type="conversation",
            entity_id=None,
            method="POST",
            variant="secondary",
            payload={"message": prompt},
        )
        for prompt in prompts
    ]
    return CRMComponent(
        component_type="clarification_notice",
        component_id=f"clarify-{uuid.uuid4().hex[:8]}",
        title=title,
        props={"reason": reason, "prompts": prompts},
        actions=actions,
    )


def _build_action_result_notice_component(*, title: str, message: str, status: str) -> CRMComponent:
    return CRMComponent(
        component_type="action_result_notice",
        component_id=f"action-result-{uuid.uuid4().hex[:8]}",
        title=title,
        props={"message": message, "status": status},
        actions=[],
    )


def _build_customer_insight_components(connection, focus_customer: dict, memory_bundle: dict) -> list[CRMComponent]:
    preferred_colors = json.loads(str(focus_customer.get("preferred_colors") or "[]"))
    preferred_categories = json.loads(str(focus_customer.get("preferred_categories") or "[]"))
    tags = _fetch_customer_tags(connection, focus_customer["id"])
    memory_notes = memory_bundle.get("memory_notes", [])

    components: list[CRMComponent] = [
        CRMComponent(
            component_type="detail_kv",
            component_id=f"customer-insight-kv-{uuid.uuid4().hex[:8]}",
            title="客户偏好摘要",
            props={
                "items": [
                    {"label": "风格偏好", "value": str(focus_customer.get("style_profile") or focus_customer.get("profile") or "--")},
                    {"label": "颜色偏好", "value": "、".join(preferred_colors) if preferred_colors else "--"},
                    {"label": "品类偏好", "value": "、".join(preferred_categories) if preferred_categories else "--"},
                    {"label": "常用触达", "value": str(focus_customer.get("preferred_channel") or "--")},
                ]
            },
        )
    ]

    if tags:
        components.append(
            CRMComponent(
                component_type="tag_group",
                component_id=f"customer-insight-tags-{uuid.uuid4().hex[:8]}",
                title="客户标签",
                props={"items": tags[:8]},
            )
        )

    if memory_notes:
        components.append(
            CRMComponent(
                component_type="memory_briefs",
                component_id=f"customer-insight-memory-{uuid.uuid4().hex[:8]}",
                title="已记录偏好与服务提示",
                props={
                    "items": [
                        {
                            "content": item["content"],
                            "note_type": item["note_type"],
                            "source": "导购补充" if item["source"] == "advisor-chat" else "历史沉淀",
                            "confidence": item["confidence"],
                        }
                        for item in memory_notes[:4]
                    ]
                },
            )
        )

    return components


def _build_rejection_response(message: str, session_id: str, reason: str, examples: list[str]) -> CRMChatResponse:
    assistant_message = CRMMessage(
        message_id=f"assistant-{uuid.uuid4().hex[:8]}",
        role="assistant",
        text=reason,
        created_at=_now(),
        ui_schema=[
            CRMComponent(
                component_type="safety_notice",
                component_id=f"safety-{uuid.uuid4().hex[:8]}",
                title="当前仅支持导购域问题",
                props={"reason": reason, "examples": examples},
            )
        ],
        meta={
            "status_hint": CONVERSATION_MODE_LABELS["safety"],
            "handoff_reason": "当前问题超出导购工作台边界，已停止下游处理。",
            "question_type": "rejection",
            "response_shape": QUESTION_TYPE_TO_RESPONSE_SHAPE["rejection"],
        },
    )
    return CRMChatResponse(
        session_id=session_id,
        messages=[
            CRMMessage(
                message_id=f"user-{uuid.uuid4().hex[:8]}",
                role="user",
                text=message,
                created_at=_now(),
                meta={},
            ),
            assistant_message,
        ],
        ui_schema=assistant_message.ui_schema,
        supported_actions=SUPPORTED_ACTIONS,
        safety_status="rejected",
        context_version=CONTEXT_VERSION,
        meta={
            "session_id": session_id,
            "question_type": "rejection",
            "response_shape": QUESTION_TYPE_TO_RESPONSE_SHAPE["rejection"],
            "conversation_mode": "safety",
            "conversation_mode_label": CONVERSATION_MODE_LABELS["safety"],
            "handoff_reason": "当前问题超出导购工作台边界，已停止下游处理。",
            "context_resolution": {},
            "focus_scope": {"customer_id": "", "product_ids": [], "task_ids": []},
            "session_snapshot": {
                "active_customer_id": "",
                "active_customer_name": "",
                "active_intent": "",
                "conversation_mode": "safety",
                "last_response_shape": QUESTION_TYPE_TO_RESPONSE_SHAPE["rejection"],
                "last_entity_ids": [],
                "handoff_reason": "当前问题超出导购工作台边界，已停止下游处理。",
                "working_memory_summary": "无工作记忆，当前已进入边界保护。",
            },
        },
    )


def _build_context_resolution_payload(resolved_context) -> dict:
    return {
        "active_customer_id": resolved_context.active_customer_id,
        "active_customer_name": resolved_context.active_customer_name,
        "reused_from_session": resolved_context.reused_from_session,
        "resolution_confidence": resolved_context.resolution_confidence,
    }


def _needs_customer_clarification(*, guardrail, message: str, resolved_context, focus_customer: dict | None) -> bool:
    if focus_customer:
        return False
    if guardrail.intent == "message_draft":
        return True
    if "她" in message or "他" in message or "这个客户" in message or "这位客户" in message:
        return True
    return False


def _determine_question_type(
    *,
    guardrail,
    focus_customer: dict | None,
    customer_inventory_request: bool,
    category_inventory_request: bool,
    customer_tag_inventory_request: bool,
    customer_preference_request: bool,
    customer_constraint_filter_request: bool,
    customer_preference_validation_request: bool,
    clarification_needed: bool,
    has_customer_candidates: bool,
    has_tasks: bool,
) -> str:
    if not guardrail.allowed:
        return "rejection"
    if clarification_needed:
        return "clarification"
    if customer_inventory_request and not focus_customer:
        return "customer_overview"
    if category_inventory_request:
        return "category_inventory"
    if customer_tag_inventory_request and not focus_customer:
        return "customer_tag_inventory"
    if customer_constraint_filter_request and not focus_customer:
        return "customer_constraint_filter"
    if customer_preference_validation_request and focus_customer:
        return "customer_preference_validation"
    if customer_preference_request and focus_customer:
        return "customer_insight"
    if guardrail.intent == "relationship_maintenance":
        return "relationship_maintenance"
    if guardrail.intent == "message_draft" and focus_customer:
        return "message_draft"
    if guardrail.intent == "task_management":
        return "task_management_with_trace" if has_tasks else "task_management"
    if guardrail.intent == "customer_filter" and has_customer_candidates:
        return "customer_filter"
    if guardrail.intent == "product_recommendation" and focus_customer:
        return "customer_product_recommendation"
    if guardrail.intent in {"product_recommendation", "inventory_lookup"}:
        return "product_recommendation"
    if focus_customer:
        return "customer_insight"
    return "customer_filter" if has_customer_candidates else "product_recommendation"


def _build_decision(
    *,
    guardrail,
    resolved_context,
    focus_customer: dict | None,
    customer_inventory_request: bool,
    category_inventory_request: bool,
    customer_tag_inventory_request: bool,
    customer_preference_request: bool,
    customer_constraint_filter_request: bool,
    customer_preference_validation_request: bool,
    clarification_needed: bool,
    customer_candidates: list[dict],
    tasks: list[dict],
) -> ChatDecision:
    question_type = _determine_question_type(
        guardrail=guardrail,
        focus_customer=focus_customer,
        customer_inventory_request=customer_inventory_request,
        category_inventory_request=category_inventory_request,
        customer_tag_inventory_request=customer_tag_inventory_request,
        customer_preference_request=customer_preference_request,
        customer_constraint_filter_request=customer_constraint_filter_request,
        customer_preference_validation_request=customer_preference_validation_request,
        clarification_needed=clarification_needed,
        has_customer_candidates=bool(customer_candidates),
        has_tasks=bool(tasks),
    )
    return ChatDecision(
        question_type=question_type,
        response_shape=QUESTION_TYPE_TO_RESPONSE_SHAPE[question_type],
        context_resolution=_build_context_resolution_payload(resolved_context),
    )


def _build_cache_key(session_id: str, normalized: str, state: dict) -> tuple[str, str, str]:
    snapshot = "|".join(
        [
            str(state.get("active_customer_id") or ""),
            str(state.get("active_intent") or ""),
            str(state.get("conversation_mode") or ""),
            str(state.get("last_response_shape") or ""),
            ",".join(state.get("last_entity_ids") or []),
            str(state.get("state_version") or 0),
            str(state.get("working_memory_summary") or ""),
        ]
    )
    return (session_id, normalized, snapshot)


def _resolve_conversation_mode(question_type: str) -> str:
    return QUESTION_TYPE_TO_CONVERSATION_MODE[question_type]


def _get_visible_products(products: list[dict], guardrail, settings) -> list[dict]:
    if guardrail.intent == "relationship_maintenance":
        return products[: settings.relationship_product_limit]
    return products[: guardrail.requested_count]


def _get_visible_tasks(tasks: list[dict], guardrail) -> list[dict]:
    return tasks[: guardrail.requested_count]


def _build_focus_scope(focus_customer: dict | None, products: list[dict], tasks: list[dict]) -> dict:
    return {
        "customer_id": focus_customer["id"] if focus_customer else "",
        "product_ids": [item["id"] for item in products],
        "task_ids": [str(item["id"]) for item in tasks],
    }


def _build_handoff_reason(
    previous_state: dict,
    question_type: str,
    conversation_mode: str,
    focus_customer: dict | None,
    resolved_context,
) -> str:
    previous_mode = str(previous_state.get("conversation_mode") or "")
    previous_customer_id = str(previous_state.get("active_customer_id") or "")
    current_customer_id = focus_customer["id"] if focus_customer else str(resolved_context.active_customer_id or "")

    if not previous_mode:
        return "本轮首次进入当前工作流。"
    if previous_customer_id and current_customer_id and previous_customer_id != current_customer_id:
        return "已切换到新的客户对象，旧客户上下文降级为历史参考。"
    if previous_mode != conversation_mode:
        if conversation_mode == "task_management":
            return "用户目标已切到任务处理，当前优先按待办链路执行。"
        if conversation_mode == "message_draft":
            return "当前已从判断阶段切到沟通整理阶段，优先组织可直接发送的话术。"
        if conversation_mode == "product_recommendation":
            return "当前已切到商品推荐阶段，优先围绕现货与风格匹配返回结果。"
        if conversation_mode == "customer_insight":
            return "当前先收口到客户画像与偏好，避免直接跳到推荐。"
        return f"当前已从上一阶段切到{CONVERSATION_MODE_LABELS.get(conversation_mode, '当前处理阶段')}。"
    if resolved_context.reused_from_session and current_customer_id:
        return "本轮沿用上一轮已锁定客户，继续围绕同一对象推进。"
    if question_type == "customer_overview":
        return "当前用户在看整体客户范围，先给总览再给样本。"
    return "当前继续沿用同一处理阶段。"


def _build_working_memory_summary(
    *,
    question_type: str,
    focus_customer: dict | None,
    guardrail,
    products: list[dict],
    tasks: list[dict],
    memory_bundle: dict,
) -> str:
    customer_name = focus_customer["name"] if focus_customer else "未锁定客户"
    product_names = "、".join(item["name"] for item in products[:2]) if products else "暂无商品焦点"
    task_names = "、".join(item["task_type"] for item in tasks[:2]) if tasks else "暂无任务焦点"
    memory_notes = "；".join(item["content"] for item in memory_bundle.get("memory_notes", [])[:2]) if memory_bundle else ""
    query_focus = "、".join([guardrail.category_hint, guardrail.season_hint, *guardrail.style_terms]).strip("、") or "无额外风格限定"
    return f"类型:{question_type} | 客户:{customer_name} | 关注:{query_focus} | 商品:{product_names} | 任务:{task_names} | 记忆:{memory_notes or '暂无'}"


def _resolve_repeat_query_mode(message: str, normalized: str, current_state: dict) -> str:
    previous_goal = _normalize_message(str(current_state.get("last_user_goal") or ""))
    compact = message.replace(" ", "")
    if any(cue in compact for cue in REPEAT_QUERY_DIVERSIFY_CUES):
        return "diversify"
    if previous_goal and previous_goal == normalized:
        return "preserve"
    return "fresh"


def _rewrite_repeat_query_message(message: str, current_state: dict) -> str:
    compact = message.replace(" ", "")
    if not any(cue in compact for cue in REPEAT_QUERY_DIVERSIFY_CUES):
        return message

    intent = str(current_state.get("active_intent") or "")
    customer_name = str(current_state.get("active_customer_name") or "")
    style_focus = str(current_state.get("last_style_focus") or "")
    focus_bits = "、".join(bit for bit in [customer_name, style_focus] if bit).strip("、")

    if intent in {"product_recommendation", "relationship_maintenance", "message_draft", "inventory_lookup"}:
        if focus_bits:
            return f"按{focus_bits}再推荐几件别的商品"
        return "再推荐几件别的商品"
    if intent == "customer_filter":
        return "再筛一批别的客户"
    if intent == "task_management":
        return "再整理一批别的待办任务"
    return message


def _resolve_stability_mode(question_type: str, repeat_query_mode: str) -> str:
    if repeat_query_mode == "diversify":
        return "entity_set_refresh"
    if question_type in {"customer_filter", "customer_overview", "customer_constraint_filter", "category_inventory", "task_management", "task_management_with_trace"}:
        return "entity_set_stable"
    if question_type in {"product_recommendation", "customer_product_recommendation", "relationship_maintenance", "message_draft"}:
        return "entity_stable_text_variable"
    return "contextual"


def _resolve_repeat_query_requested_count(current_state: dict, default: int) -> int:
    active_product_ids = current_state.get("active_product_ids") or []
    active_task_ids = current_state.get("active_task_ids") or []
    last_entity_ids = current_state.get("last_entity_ids") or []
    return len(active_product_ids) or len(active_task_ids) or len(last_entity_ids) or default


def _build_response_meta(
    *,
    session_id: str,
    decision: ChatDecision,
    conversation_mode: str,
    handoff_reason: str,
    working_memory_summary: str,
    focus_scope: dict,
    current_state: dict,
    focus_customer: dict | None,
    resolved_context,
    guardrail,
    clarification_needed: bool,
    repeat_query_mode: str,
    stability_mode: str,
) -> dict:
    next_state_version = int(current_state.get("state_version") or 0) + 1
    active_customer_id = focus_customer["id"] if focus_customer else resolved_context.active_customer_id
    active_customer_name = focus_customer["name"] if focus_customer else resolved_context.active_customer_name
    session_snapshot = {
        "active_customer_id": active_customer_id,
        "active_customer_name": active_customer_name,
        "active_intent": guardrail.intent,
        "conversation_mode": conversation_mode,
        "last_response_shape": decision.response_shape,
        "last_entity_ids": _dedupe_preserve_order(
            [
                *( [focus_scope["customer_id"]] if focus_scope["customer_id"] else [] ),
                *focus_scope["product_ids"],
                *focus_scope["task_ids"],
            ]
        ),
        "handoff_reason": handoff_reason,
        "state_version": next_state_version,
        "working_memory_summary": working_memory_summary,
    }
    return {
        "session_id": session_id,
        "question_type": decision.question_type,
        "response_shape": decision.response_shape,
        "conversation_mode": conversation_mode,
        "conversation_mode_label": CONVERSATION_MODE_LABELS.get(conversation_mode, "继续处理"),
        "handoff_reason": handoff_reason,
        "context_resolution": decision.context_resolution,
        "focus_scope": focus_scope,
        "clarification_needed": clarification_needed,
        "repeat_query_mode": repeat_query_mode,
        "stability_mode": stability_mode,
        "session_snapshot": session_snapshot,
    }


def send_chat(message: str, session_id: str = None, *, actor: RequestActor | None = None) -> CRMChatResponse:
    settings = get_app_settings()
    current_session_id = session_id or f"s_{uuid.uuid4().hex[:10]}"
    current_actor = actor or RequestActor(advisor_id=settings.advisor_id, store_id=settings.store_id)
    with get_connection() as connection:
        ensure_session(
            connection,
            current_session_id,
            current_actor.advisor_id,
            settings.advisor_name,
            current_actor.store_id,
            settings.store_name,
        )
        current_state = get_session_state(connection, current_session_id)
        repeat_query_mode = _resolve_repeat_query_mode(message, _normalize_message(message), current_state)
        route_message = _rewrite_repeat_query_message(message, current_state)
        normalized = _normalize_message(route_message)
        guardrail = evaluate_message(route_message, settings.brand_name)
        if repeat_query_mode == "diversify":
            guardrail = replace(
                guardrail,
                requested_count=_resolve_repeat_query_requested_count(current_state, guardrail.requested_count),
            )
        provisional_cache_key = _build_cache_key(current_session_id, normalized, current_state)
        cached = RESPONSE_CACHE.get(provisional_cache_key) if repeat_query_mode == "fresh" else None
        if cached:
            return cached.model_copy(deep=True)
        if not guardrail.allowed:
            response = _build_rejection_response(message, current_session_id, guardrail.reason, guardrail.examples)
            next_state_version = int(current_state.get("state_version") or 0) + 1
            add_turn(connection, current_session_id, "user", message, f"拒绝：{message[:48]}")
            add_turn(connection, current_session_id, "assistant", guardrail.reason, guardrail.reason)
            add_conversation_checkpoint(
                connection,
                current_session_id,
                workflow_name="safety",
                workflow_stage="rejected",
                user_goal=route_message[:160],
                assistant_summary=guardrail.reason[:160],
                result_summary="已停止处理",
                next_step="引导回到导购域问题。",
            )
            update_session_state(
                connection,
                current_session_id,
                active_customer_id=current_state.get("active_customer_id"),
                active_customer_name=str(current_state.get("active_customer_name") or ""),
                active_intent="rejection",
                active_product_ids=current_state.get("active_product_ids") or [],
                active_task_ids=current_state.get("active_task_ids") or [],
                last_style_focus=str(current_state.get("last_style_focus") or ""),
                resolution_confidence="high",
                workflow_name="safety",
                workflow_stage="rejected",
                last_user_goal=route_message[:160],
                last_response_shape=QUESTION_TYPE_TO_RESPONSE_SHAPE["rejection"],
                last_entity_ids=current_state.get("last_entity_ids") or [],
                conversation_mode="safety",
                handoff_reason="当前问题超出导购工作台边界，已停止下游处理。",
                state_version=next_state_version,
                working_memory_summary="无工作记忆，当前已进入边界保护。",
            )
            add_audit_event(
                connection,
                advisor_id=current_actor.advisor_id,
                store_id=current_actor.store_id,
                action_type="chat_rejected",
                entity_type="session",
                entity_id=current_session_id,
                session_id=current_session_id,
                before_summary=str(current_state.get("conversation_mode") or ""),
                after_summary="safety",
            )
            response.meta["session_snapshot"]["state_version"] = next_state_version
            response.meta["session_snapshot"]["active_customer_id"] = current_state.get("active_customer_id") or ""
            response.meta["session_snapshot"]["active_customer_name"] = current_state.get("active_customer_name") or ""
            response.meta["session_snapshot"]["active_intent"] = "rejection"
            response.meta["state_version"] = next_state_version
            RESPONSE_CACHE[provisional_cache_key] = response.model_copy(deep=True)
            return response

        add_turn(connection, current_session_id, "user", message, message[:80])
        summaries = get_recent_turn_summaries(connection, current_session_id)
        named_customer_ids = _find_named_customer_ids(connection, route_message, limit=1)
        customer_lookup = _fetch_customer_name_map(connection, named_customer_ids)
        resolved_context = resolve_turn_context(
            connection,
            current_session_id,
            route_message,
            named_customer_ids=named_customer_ids,
            customer_lookup=customer_lookup,
        )
        resolved_customer_ids = [resolved_context.active_customer_id] if resolved_context.active_customer_id else []
        customer_inventory_request = _is_customer_inventory_request(route_message)
        category_inventory_request = _is_category_inventory_request(route_message)
        customer_tag_inventory_request = _is_customer_tag_inventory_request(route_message)
        customer_preference_request = _is_customer_preference_request(route_message)
        customer_constraint_filter_request = _is_customer_constraint_filter_request(route_message)
        customer_preference_validation_request = _is_customer_preference_validation_request(route_message)
        excluded_product_ids = current_state.get("active_product_ids", []) if repeat_query_mode == "diversify" else []
        excluded_customer_ids = (
            current_state.get("last_entity_ids", [])
            if repeat_query_mode == "diversify" and current_state.get("active_intent") == "customer_filter"
            else []
        )

        effective_query_tasks = guardrail.intent == "task_management"
        effective_query_customers = (
            guardrail.intent in {"customer_filter", "message_draft", "relationship_maintenance"}
            or customer_constraint_filter_request
            or bool(resolved_customer_ids)
        )
        effective_query_products = (
            guardrail.intent in {"product_recommendation", "inventory_lookup", "message_draft", "relationship_maintenance"}
            or (is_relationship_maintenance_request(route_message) and bool(resolved_customer_ids))
        )
        if customer_constraint_filter_request and not resolved_customer_ids:
            effective_query_products = False

        customer_candidates = (
            _query_customer_candidates(
                connection,
                route_message,
                limit=(
                    1
                    if resolved_customer_ids
                    else settings.customer_sample_limit
                    if customer_inventory_request
                    else guardrail.requested_count
                ),
                customer_ids=resolved_customer_ids or None,
                exclude_ids=excluded_customer_ids or None,
            )
            if effective_query_customers
            else []
        )
        focus_customer = customer_candidates[0] if resolved_customer_ids and customer_candidates else None
        if customer_constraint_filter_request and not focus_customer:
            effective_query_products = False
        clarification_needed = _needs_customer_clarification(
            guardrail=guardrail,
            message=route_message,
            resolved_context=resolved_context,
            focus_customer=focus_customer,
        )
        memory_bundle = get_customer_memory_bundle(connection, focus_customer["id"]) if focus_customer else {}
        memory_preferences = extract_preference_signals(memory_bundle) if memory_bundle else None
        products = (
            _query_products(
                connection,
                route_message,
                limit=(
                    min(guardrail.requested_count, settings.relationship_product_limit)
                    if guardrail.intent == "relationship_maintenance"
                    else guardrail.requested_count
                ),
                category_hint=guardrail.category_hint,
                season_hint=guardrail.season_hint,
                query_terms=guardrail.query_terms or guardrail.style_terms,
                focus_customer=focus_customer,
                memory_preferences=memory_preferences,
                exclude_ids=excluded_product_ids or None,
            )
            if effective_query_products
            else []
        )
        tasks = _query_tasks(connection, limit=guardrail.requested_count if effective_query_tasks else 0) if effective_query_tasks else []
        visible_products = _get_visible_products(products, guardrail, settings)
        visible_tasks = _get_visible_tasks(tasks, guardrail)
        workflow = resolve_workflow(
            intent=guardrail.intent,
            message=route_message,
            focus_customer=focus_customer,
            products=products,
            tasks=tasks,
        )
        knowledge_briefs = retrieve_knowledge_briefs(
            connection,
            message=route_message,
            workflow_name=workflow.workflow_name,
            focus_customer=focus_customer,
            limit=3,
        )
        memory_note = extract_memory_note_update(
            route_message,
            focus_customer["name"] if focus_customer else resolved_context.active_customer_name,
        )
        memory_suggestion = extract_memory_suggestion(
            route_message,
            focus_customer["name"] if focus_customer else resolved_context.active_customer_name,
        )
        memory_only_turn = _is_pure_memory_update_turn(route_message, memory_note)
        memory_conflict_note = ""
        decision = _build_decision(
            guardrail=guardrail,
            resolved_context=resolved_context,
            focus_customer=focus_customer,
            customer_inventory_request=customer_inventory_request,
            category_inventory_request=category_inventory_request,
            customer_tag_inventory_request=customer_tag_inventory_request,
            customer_preference_request=customer_preference_request,
            customer_constraint_filter_request=customer_constraint_filter_request,
            customer_preference_validation_request=customer_preference_validation_request,
            clarification_needed=clarification_needed,
            customer_candidates=customer_candidates,
            tasks=tasks,
        )
        conversation_mode = _resolve_conversation_mode(decision.question_type)
        focus_scope = _build_focus_scope(focus_customer, visible_products, visible_tasks)
        handoff_reason = _build_handoff_reason(
            current_state,
            decision.question_type,
            conversation_mode,
            focus_customer,
            resolved_context,
        )
        if repeat_query_mode == "diversify":
            handoff_reason = "用户明确要求换一批结果，当前在保留原条件的前提下返回新的候选。"
        working_memory_summary = _build_working_memory_summary(
            question_type=decision.question_type,
            focus_customer=focus_customer,
            guardrail=guardrail,
            products=products,
            tasks=tasks,
            memory_bundle=memory_bundle,
        )
        layered_memory = (
            get_layered_memory_bundle(
                connection,
                focus_customer["id"],
                current_session_id,
                working_memory_summary=working_memory_summary,
            )
            if focus_customer
            else None
        )
        customer_memory_summary = "；".join(item["content"] for item in memory_bundle.get("memory_notes", [])[:2])
        session_memory_summary = "；".join(item["content"] for item in (layered_memory.session_notes if layered_memory else [])[:2])

        components: list[CRMComponent] = []
        intent_label = guardrail.intent_label

        if decision.question_type == "clarification":
            components = [
                _build_clarification_component(
                    "还需要补充一个关键信息",
                    "当前还没有锁定具体客户，先告诉我要继续跟进哪位客户，我再帮你整理推荐或沟通内容。",
                    [
                        "帮我给乔安禾发条消息",
                        "按乔知夏的喜好推荐几件产品",
                        "我要维护一下乔安禾的客户关系",
                    ],
                )
            ]
        elif focus_customer:
            components.append(
                CRMComponent(
                    component_type="customer_spotlight",
                    component_id=f"customer-focus-{uuid.uuid4().hex[:8]}",
                    title=f"{focus_customer['name']} 当前画像",
                    props={"item": focus_customer},
                    actions=[],
                )
            )
            if decision.question_type in {"customer_insight", "customer_preference_validation"}:
                components.extend(_build_customer_insight_components(connection, focus_customer, memory_bundle))
            if not memory_only_turn and decision.question_type in {
                "relationship_maintenance",
                "customer_product_recommendation",
                "message_draft",
            }:
                components.append(
                    _build_workflow_checkpoint_component(
                        workflow=workflow,
                        user_goal=route_message,
                        focus_customer=focus_customer,
                        products=visible_products,
                        tasks=visible_tasks,
                        memory_bundle=memory_bundle,
                    )
                )
            if decision.question_type == "relationship_maintenance":
                components.append(
                    _build_relationship_plan_component(
                        focus_customer,
                        memory_bundle,
                        products[:2],
                        workflow.next_step,
                    )
                )
        elif customer_candidates:
            if decision.question_type in {"customer_filter", "customer_overview", "customer_constraint_filter"}:
                components.append(
                    _build_workflow_checkpoint_component(
                        workflow=workflow,
                        user_goal=route_message,
                        focus_customer=None,
                        products=[],
                        tasks=[],
                        memory_bundle={},
                    )
                )
            components.append(
                CRMComponent(
                    component_type="customer_list",
                    component_id=f"customers-{uuid.uuid4().hex[:8]}",
                    title="建议优先跟进客户",
                    props={"items": customer_candidates},
                    actions=[],
                )
            )
        elif decision.question_type in {"task_management", "task_management_with_trace"} and tasks:
            components.append(
                    _build_workflow_checkpoint_component(
                        workflow=workflow,
                        user_goal=route_message,
                        focus_customer=None,
                        products=[],
                        tasks=visible_tasks,
                        memory_bundle={},
                    )
        )
        if knowledge_briefs and decision.question_type == "relationship_maintenance":
            components.append(_build_knowledge_briefs_component(knowledge_briefs))
        if decision.question_type == "customer_overview" and not focus_customer:
            overview = _get_customer_pool_overview(connection)
            components.insert(
                0,
                CRMComponent(
                    component_type="customer_overview",
                    component_id=f"customer-overview-{uuid.uuid4().hex[:8]}",
                    title="客户池概览",
                    props=overview,
                ),
            )
        if decision.question_type == "customer_constraint_filter" and components:
            components[0].title = "符合约束的客户"
        if decision.question_type == "customer_tag_inventory" and not focus_customer:
            components = [
                CRMComponent(
                    component_type="tag_group",
                    component_id=f"customer-tag-overview-{uuid.uuid4().hex[:8]}",
                    title="当前客户标签",
                    props={"items": _get_customer_tag_overview(connection)},
                )
            ]
        if decision.question_type == "category_inventory":
            category_overview = _get_category_overview(connection)
            components = [
                CRMComponent(
                    component_type="category_overview",
                    component_id=f"category-overview-{uuid.uuid4().hex[:8]}",
                    title="当前可推荐品类",
                    props=category_overview,
                )
            ]
        if memory_suggestion and focus_customer:
            add_customer_memory_suggestion(
                connection,
                focus_customer["id"],
                "preference_hint",
                memory_suggestion,
                source="advisor-observation",
                source_session_id=current_session_id,
                confidence="low",
            )
            _persist_memory_facts(
                connection,
                customer_id=focus_customer["id"],
                note=memory_suggestion,
                source_type="advisor-observation",
                source_session_id=current_session_id,
                status="pending",
                confidence="low",
            )
            pending_suggestions = get_customer_memory_suggestions(
                connection,
                focus_customer["id"],
                limit=4,
                session_id=current_session_id,
            )
            if pending_suggestions and not memory_only_turn:
                components.append(_build_memory_suggestions_component(focus_customer, pending_suggestions))
        if products and decision.question_type not in {"category_inventory", "customer_insight", "customer_tag_inventory"}:
            components.append(
                CRMComponent(
                    component_type="product_grid",
                    component_id=f"products-{uuid.uuid4().hex[:8]}",
                    title=(
                        f"给{focus_customer['name']}的推荐单品"
                        if focus_customer
                        else "可直接推荐的门店单品" if not guardrail.season_hint else f"{guardrail.season_hint}可优先推荐的门店单品"
                    ),
                    props={"items": visible_products},
                )
            )
        if decision.question_type in {"task_management", "task_management_with_trace"}:
            components.append(
                CRMComponent(
                    component_type="task_list",
                    component_id=f"tasks-{uuid.uuid4().hex[:8]}",
                    title="待处理任务",
                    props={"items": visible_tasks},
                )
            )

        top_customer = customer_candidates[0] if customer_candidates else None
        recommended_product_names = [item["name"] for item in products[:3]]
        if top_customer and (decision.question_type == "message_draft" or _should_include_message_draft(guardrail, message)):
            fallback_draft = (
                f"{top_customer['name']}，你好，这周店里到了几款更适合你通勤穿着的新单品，"
                f"我先帮你挑了 {recommended_product_names[0] if recommended_product_names else '两款重点推荐'}，"
                "如果你方便，我发你细节看看。"
            )
            draft_text, _ = generate_message_draft(
                top_customer["name"],
                recommended_product_names,
                "自然克制",
                fallback_draft,
                conversation_mode=CONVERSATION_MODE_LABELS.get(conversation_mode, conversation_mode),
                confirmed_memory=customer_memory_summary[:140],
                observed_memory=session_memory_summary[:140],
            )
            components.append(
                CRMComponent(
                    component_type="message_draft",
                    component_id=f"draft-{uuid.uuid4().hex[:8]}",
                    title="建议沟通话术",
                    props={"text": draft_text},
                )
            )

        knowledge_summary = "；".join(item.content for item in knowledge_briefs[:2])
        summary_seed = (
            f"客户 {len(customer_candidates)} 人，商品 {len(products)} 款，任务 {len(tasks)} 条。"
            f" 最近上下文：{'；'.join(summaries[-3:])[:180]}。"
            f" 客户记忆：{customer_memory_summary[:140]}"
            f" 会话记忆：{session_memory_summary[:140]}"
            f" 工作流：{workflow.workflow_name}/{workflow.workflow_stage}，{workflow.rationale}。"
            f" 切换原因：{handoff_reason[:120]}。"
            f" 工作记忆：{working_memory_summary[:180]}。"
            f" 导购经验：{knowledge_summary[:140]}"
        )
        if decision.question_type == "relationship_maintenance" and focus_customer:
            fallback_summary = (
                f"这轮建议先围绕 {focus_customer['name']} 的既有偏好做轻触达，"
                "先关怀再带一到两件更贴合的现货，避免一次推太满。"
            )
        elif decision.question_type == "customer_overview":
            overview = _get_customer_pool_overview(connection)
            total_customers = overview["total_customers"]
            sample_limit = overview["sample_limit"]
            fallback_summary = f"当前门店共有 {total_customers} 位客户，先展示其中 {sample_limit} 位代表客户，后续可以继续按层级、标签和状态细分筛选。"
        elif decision.question_type == "customer_tag_inventory":
            fallback_summary = "当前先展示客户池里最常见的一组标签，后续可以继续指定某位客户查看更细的偏好与服务记录。"
        elif decision.question_type == "category_inventory":
            total_categories = _get_category_overview(connection)["total_categories"]
            fallback_summary = f"当前门店共有 {total_categories} 个可推荐品类，我先按品类和库存把范围展示出来，后续可以继续指定风格、季节或客户偏好。"
        elif decision.question_type in {"customer_insight", "customer_preference_validation"} and focus_customer:
            fallback_summary = f"已整理 {focus_customer['name']} 的偏好、标签和服务记录，可以直接据此继续做推荐或生成沟通内容。"
        elif decision.question_type == "customer_constraint_filter":
            fallback_summary = "已先按客户约束做了一轮筛选，你可以继续指定风格、场景或跟进状态来缩小范围。"
        elif decision.question_type == "clarification":
            fallback_summary = "还需要先锁定具体客户，我再继续整理推荐或沟通内容。"
        elif decision.question_type in {"task_management", "task_management_with_trace"}:
            fallback_summary = "已按到期时间和优先级整理当前待处理任务，可直接逐条执行。"
        elif decision.question_type in {"customer_filter", "customer_product_recommendation", "product_recommendation", "message_draft"}:
            fallback_summary = "已按门店现有客户、商品和任务数据整理出一组可直接执行的跟进建议。"
        else:
            fallback_summary = "已按门店现有客户、商品和任务数据整理出一组可直接执行的跟进建议。"
        if memory_note and (focus_customer or resolved_context.active_customer_id):
            target_customer_id = focus_customer["id"] if focus_customer else str(resolved_context.active_customer_id)
            target_name = focus_customer["name"] if focus_customer else resolved_context.active_customer_name or "该客户"
            conflict_reason = detect_memory_conflict(memory_note, memory_bundle) if memory_bundle else None
            if conflict_reason:
                memory_conflict_note = conflict_reason
                add_customer_memory_suggestion(
                    connection,
                    target_customer_id,
                    "advisor_note_conflict",
                    memory_note,
                    source="advisor-chat-conflict",
                    source_session_id=current_session_id,
                    confidence="medium",
                )
                _persist_memory_facts(
                    connection,
                    customer_id=target_customer_id,
                    note=memory_note,
                    source_type="advisor-chat-conflict",
                    source_session_id=current_session_id,
                    status="pending",
                    confidence="medium",
                )
                if focus_customer:
                    pending_suggestions = get_customer_memory_suggestions(
                        connection,
                        focus_customer["id"],
                        limit=4,
                        session_id=current_session_id,
                    )
                    if pending_suggestions:
                        components.append(_build_memory_suggestions_component(focus_customer, pending_suggestions))
                fallback_summary = f"已记录 {target_name} 的新观察，但它与已有偏好存在冲突，当前先作为待确认信息保留。"
            else:
                add_customer_memory_note(
                    connection,
                    target_customer_id,
                    "advisor_note",
                    memory_note,
                    source="advisor-chat",
                    confidence="medium",
                    pinned=False,
                )
                _persist_memory_facts(
                    connection,
                    customer_id=target_customer_id,
                    note=memory_note,
                    source_type="advisor-chat",
                    source_session_id=current_session_id,
                    status="confirmed",
                    confidence="medium",
                    confirmed_by=current_actor.advisor_id,
                )
                fallback_summary = f"已记住 {target_name} 的新偏好，后续推荐会优先按这条备注执行。"
        memory_only_turn = _is_pure_memory_update_turn(message, memory_note)
        if memory_only_turn and focus_customer:
            components = [
                component
                for component in components
                if component.component_type in {"customer_spotlight", "memory_suggestions"}
            ]
        if memory_only_turn and memory_note:
            summary_text = _compact_assistant_summary(fallback_summary, fallback_summary)
        else:
            summary_text, _ = generate_assistant_brief(
                intent_label,
                route_message,
                summary_seed,
                fallback_summary,
                customer_name=focus_customer["name"] if focus_customer else "",
                conversation_mode=CONVERSATION_MODE_LABELS.get(conversation_mode, conversation_mode),
                handoff_reason=handoff_reason,
                confirmed_memory=customer_memory_summary[:140],
                observed_memory=(session_memory_summary or memory_conflict_note)[:140],
            )
            summary_text = _compact_assistant_summary(summary_text, fallback_summary)
        if _should_include_trace(route_message):
            components.append(_build_trace_components(guardrail, len(customer_candidates) + len(products) + len(tasks)))

        assistant_message = CRMMessage(
            message_id=f"assistant-{uuid.uuid4().hex[:8]}",
            role="assistant",
            text=summary_text,
            created_at=_now(),
            ui_schema=components,
            meta={
                "status_hint": CONVERSATION_MODE_LABELS.get(conversation_mode, "继续处理"),
                "handoff_reason": handoff_reason,
                "question_type": decision.question_type,
                "response_shape": decision.response_shape,
            },
        )
        response_meta = _build_response_meta(
            session_id=current_session_id,
            decision=decision,
            conversation_mode=conversation_mode,
            handoff_reason=handoff_reason,
            working_memory_summary=working_memory_summary,
            focus_scope=focus_scope,
            current_state=current_state,
            focus_customer=focus_customer,
            resolved_context=resolved_context,
            guardrail=guardrail,
            clarification_needed=clarification_needed,
            repeat_query_mode=repeat_query_mode,
            stability_mode=_resolve_stability_mode(decision.question_type, repeat_query_mode),
        )
        response = CRMChatResponse(
            session_id=current_session_id,
            messages=[
                CRMMessage(
                    message_id=f"user-{uuid.uuid4().hex[:8]}",
                    role="user",
                    text=message,
                    created_at=_now(),
                    meta={},
                ),
                assistant_message,
            ],
            ui_schema=components,
            supported_actions=SUPPORTED_ACTIONS,
            safety_status="allowed",
            context_version=CONTEXT_VERSION,
            meta=response_meta,
            clarification_needed=clarification_needed,
        )
        add_turn(connection, current_session_id, "assistant", summary_text, summary_text[:80])
        add_conversation_checkpoint(
            connection,
            current_session_id,
            workflow_name=workflow.workflow_name,
            workflow_stage=workflow.workflow_stage,
            user_goal=route_message[:160],
            assistant_summary=summary_text[:160],
            focus_customer_id=focus_customer["id"] if focus_customer else "",
            focus_customer_name=focus_customer["name"] if focus_customer else "",
            result_summary=f"客户 {1 if focus_customer else len(customer_candidates)} · 商品 {len(products)} · 任务 {len(tasks)}",
            next_step=workflow.next_step[:160],
        )
        style_focus = "、".join(guardrail.style_terms[:2]) or guardrail.category_hint or guardrail.season_hint
        update_session_state(
            connection,
            current_session_id,
            active_customer_id=focus_customer["id"] if focus_customer else resolved_context.active_customer_id,
            active_customer_name=focus_customer["name"] if focus_customer else resolved_context.active_customer_name,
            active_intent=guardrail.intent,
            active_product_ids=[item["id"] for item in visible_products],
            active_task_ids=[str(item["id"]) for item in visible_tasks],
            last_style_focus=style_focus,
            resolution_confidence=resolved_context.resolution_confidence,
            workflow_name=workflow.workflow_name,
            workflow_stage=workflow.workflow_stage,
            last_user_goal=route_message[:160],
            last_response_shape=decision.response_shape,
            last_entity_ids=_dedupe_preserve_order(
                [
                    *( [focus_customer["id"]] if focus_customer else [] ),
                    *[item["id"] for item in customer_candidates],
                    *[item["id"] for item in visible_products],
                    *[str(item["id"]) for item in visible_tasks],
                ]
            ),
            conversation_mode=conversation_mode,
            handoff_reason=handoff_reason,
            state_version=int(response_meta["session_snapshot"]["state_version"]),
            working_memory_summary=working_memory_summary,
        )


    final_entity_ids: list[str] = []
    if "focus_customer" in locals() and focus_customer:
        final_entity_ids.append(focus_customer["id"])
    if "customer_candidates" in locals():
        final_entity_ids.extend(item["id"] for item in customer_candidates)
    if "visible_products" in locals():
        final_entity_ids.extend(item["id"] for item in visible_products)
    if "visible_tasks" in locals():
        final_entity_ids.extend(str(item["id"]) for item in visible_tasks)

    final_cache_key = _build_cache_key(
        current_session_id,
        normalized,
        {
            "active_customer_id": focus_customer["id"] if "focus_customer" in locals() and focus_customer else str(resolved_context.active_customer_id or ""),
            "active_intent": guardrail.intent,
            "last_response_shape": decision.response_shape if "decision" in locals() else "",
            "last_entity_ids": _dedupe_preserve_order(final_entity_ids),
            "conversation_mode": conversation_mode if "conversation_mode" in locals() else "",
            "handoff_reason": handoff_reason if "handoff_reason" in locals() else "",
            "state_version": int(response_meta["session_snapshot"]["state_version"]) if "response_meta" in locals() else 0,
            "working_memory_summary": working_memory_summary if "working_memory_summary" in locals() else "",
        },
    )
    RESPONSE_CACHE[final_cache_key] = response.model_copy(deep=True)
    return response


def get_customer_detail(customer_id: str) -> EntityDetailResponse:
    with get_connection() as connection:
        row = row_to_dict(
            connection.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        )
        if row is None:
            raise KeyError(customer_id)
        tags = _fetch_customer_tags(connection, customer_id)
        logs = [
            dict(item)
            for item in connection.execute(
                """
                SELECT channel, summary, created_at
                FROM interaction_logs
                WHERE customer_id = ?
                ORDER BY created_at DESC
                LIMIT 3
                """,
                (customer_id,),
            ).fetchall()
        ]
        tasks = [
            dict(item)
            for item in connection.execute(
                """
                SELECT id, task_type, due_date, priority, status
                FROM follow_up_tasks
                WHERE customer_id = ?
                ORDER BY due_date ASC
                LIMIT 3
                """,
                (customer_id,),
            ).fetchall()
        ]
        memory_notes = get_customer_memory_notes(connection, customer_id, limit=6)
        memory_suggestions = get_customer_memory_suggestions(connection, customer_id, limit=6)

    return EntityDetailResponse(
        entity_type="customer",
        entity_id=customer_id,
        title=row["name"],
        subtitle=f"{row['tier']}会员 · {row['store_name']}",
        summary=f"偏好 {row['style_profile']}，累计消费 {row['lifetime_value']}。",
        ui_schema=[
            CRMComponent(
                component_type="detail_kv",
                component_id=f"customer-kv-{customer_id}",
                title="客户概览",
                props={
                    "items": [
                        {"label": "风格偏好", "value": row["style_profile"]},
                        {"label": "颜色偏好", "value": "、".join(json.loads(row["preferred_colors"]))},
                        {"label": "品类偏好", "value": "、".join(json.loads(row["preferred_categories"]))},
                        {"label": "尺码备注", "value": row["size_note"]},
                        {"label": "常用触达", "value": row["preferred_channel"]},
                    ]
                },
            ),
            CRMComponent(
                component_type="tag_group",
                component_id=f"customer-tags-{customer_id}",
                title="客户标签",
                props={"items": tags},
            ),
            CRMComponent(
                component_type="timeline",
                component_id=f"customer-logs-{customer_id}",
                title="最近互动",
                props={"items": logs},
            ),
            CRMComponent(
                component_type="memory_briefs",
                component_id=f"customer-memory-{customer_id}",
                title="已记录偏好与服务提示",
                props={
                    "items": [
                        {
                            "content": item["content"],
                            "note_type": item["note_type"],
                            "source": "导购补充" if item["source"] == "advisor-chat" else "历史沉淀",
                            "confidence": item["confidence"],
                        }
                        for item in memory_notes
                    ]
                },
            ),
            CRMComponent(
                component_type="memory_suggestions",
                component_id=f"customer-memory-suggestions-{customer_id}",
                title="待确认记录",
                props={
                    "items": [
                        {
                            "id": item["id"],
                            "content": item["content"],
                            "note_type": item["note_type"],
                            "source": "本轮观察",
                            "confidence": item["confidence"],
                            "customer_id": customer_id,
                        }
                        for item in memory_suggestions
                    ]
                },
            ),
            CRMComponent(
                component_type="task_list",
                component_id=f"customer-tasks-{customer_id}",
                title="关联任务",
                props={"items": tasks},
            ),
        ],
    )


def get_product_detail(product_id: str) -> EntityDetailResponse:
    with get_connection() as connection:
        row = row_to_dict(
            connection.execute(
                """
                SELECT p.*, i.availability, i.store_stock, i.warehouse_stock
                FROM products p
                JOIN inventory i ON i.product_id = p.id
                WHERE p.id = ?
                """,
                (product_id,),
            ).fetchone()
        )
        if row is None:
            raise KeyError(product_id)

    return EntityDetailResponse(
        entity_type="product",
        entity_id=product_id,
        title=row["name"],
        subtitle=f"{row['category']} · {row['color']} · ¥{row['price']}",
        summary=row["summary"],
        ui_schema=[
            CRMComponent(
                component_type="image_panel",
                component_id=f"product-image-{product_id}",
                title="商品图",
                props={"image_url": row["image_url"], "alt": row["name"]},
            ),
            CRMComponent(
                component_type="detail_kv",
                component_id=f"product-kv-{product_id}",
                title="商品信息",
                props={
                    "items": [
                        {"label": "系列", "value": row["collection_name"]},
                        {"label": "库存状态", "value": row["availability"]},
                        {"label": "门店库存", "value": str(row["store_stock"])},
                        {"label": "仓库库存", "value": str(row["warehouse_stock"])},
                        {"label": "图源", "value": row["image_source_name"]},
                    ]
                },
            ),
            CRMComponent(
                component_type="tag_group",
                component_id=f"product-tags-{product_id}",
                title="风格标签",
                props={"items": json.loads(row["style_tags"])},
            ),
        ],
    )


def get_task_detail(task_id: str) -> EntityDetailResponse:
    with get_connection() as connection:
        row = row_to_dict(
            connection.execute(
                """
                SELECT t.*, c.name AS customer_name, c.tier AS customer_tier
                FROM follow_up_tasks t
                JOIN customers c ON c.id = t.customer_id
                WHERE t.id = ?
                """,
                (task_id,),
            ).fetchone()
        )
        if row is None:
            raise KeyError(task_id)
        product_names = _fetch_product_names(connection, json.loads(row["recommended_product_ids"]))

    return EntityDetailResponse(
        entity_type="task",
        entity_id=task_id,
        title=row["task_type"],
        subtitle=f"{row['customer_name']} · 优先级 {row['priority']}",
        summary=row["reason"],
        ui_schema=[
            CRMComponent(
                component_type="detail_kv",
                component_id=f"task-kv-{task_id}",
                title="任务信息",
                props={
                    "items": [
                        {"label": "客户", "value": row["customer_name"]},
                        {"label": "会员层级", "value": row["customer_tier"]},
                        {"label": "到期日", "value": row["due_date"]},
                        {"label": "状态", "value": row["status"]},
                        {"label": "建议语气", "value": row["suggested_tone"]},
                    ]
                },
            ),
            CRMComponent(
                component_type="tag_group",
                component_id=f"task-products-{task_id}",
                title="关联推荐单品",
                props={"items": product_names},
            ),
        ],
    )


def complete_task(task_id: str, *, actor: RequestActor) -> TaskCompleteResponse:
    settings = get_app_settings()
    with get_connection() as connection:
        row = row_to_dict(
            connection.execute(
                """
                SELECT t.*, c.name AS customer_name, c.store_name
                FROM follow_up_tasks t
                JOIN customers c ON c.id = t.customer_id
                WHERE t.id = ?
                """,
                (task_id,),
            ).fetchone()
        )
        if row is None:
            raise KeyError(task_id)
        if str(row["store_name"]) != settings.store_name:
            raise KeyError(task_id)

        previous_status = str(row["status"])
        connection.execute("UPDATE follow_up_tasks SET status = 'done' WHERE id = ?", (task_id,))
        related_session_ids = find_related_session_ids(
            connection,
            customer_id=str(row["customer_id"]),
            task_id=task_id,
        )
        bump_session_state_versions(connection, related_session_ids)
        session_meta = _build_mutation_session_meta(connection, related_session_ids)
        add_audit_event(
            connection,
            advisor_id=actor.advisor_id,
            store_id=actor.store_id,
            action_type="complete_task",
            entity_type="task",
            entity_id=task_id,
            session_id=str(session_meta.get("session_id") or ""),
            before_summary=previous_status,
            after_summary="done",
        )

    _invalidate_cache_for_sessions(related_session_ids)
    return TaskCompleteResponse(
        task_id=task_id,
        status="done",
        message="任务已标记完成，并同步更新到工作台。",
        updated_component=_build_action_result_notice_component(
            title="任务状态已更新",
            message=f"{row['customer_name']} 的“{row['task_type']}”已完成，后续列表和会话会按最新状态刷新。",
            status="success",
        ),
        session_meta=session_meta,
    )


def get_session_detail(session_id: str) -> EntityDetailResponse:
    with get_connection() as connection:
        state = get_session_state(connection, session_id)
        session_row = row_to_dict(
            connection.execute(
                "SELECT id, advisor_name, store_name, created_at, updated_at FROM conversation_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        )
        if session_row is None:
            raise KeyError(session_id)
        checkpoints = get_conversation_checkpoints(connection, session_id, limit=12)

    return EntityDetailResponse(
        entity_type="session",
        entity_id=session_id,
        title="会话节点",
        subtitle=f"{session_row['advisor_name']} · {session_row['store_name']}",
        summary="把这轮导购过程拆成可回看的节点，方便确认当前阶段、结果规模和下一步动作。",
        ui_schema=[
            CRMComponent(
                component_type="detail_kv",
                component_id=f"session-kv-{session_id}",
                title="当前会话状态",
                props={
                    "items": [
                        {"label": "当前客户", "value": state.get("active_customer_name") or "未锁定"},
                        {"label": "当前意图", "value": state.get("active_intent") or "未识别"},
                        {"label": "当前模式", "value": CONVERSATION_MODE_LABELS.get(state.get("conversation_mode") or "", "未进入") if state.get("conversation_mode") else "未进入"},
                        {"label": "工作流", "value": f"{state.get('workflow_name') or '-'} / {state.get('workflow_stage') or '-'}"},
                        {"label": "最近目标", "value": state.get("last_user_goal") or "暂无"},
                        {"label": "返回形态", "value": state.get("last_response_shape") or "暂无"},
                        {"label": "最近实体", "value": "、".join(state.get("last_entity_ids") or []) or "暂无"},
                        {"label": "切换原因", "value": state.get("handoff_reason") or "暂无"},
                        {"label": "工作记忆", "value": state.get("working_memory_summary") or "暂无"},
                    ]
                },
            ),
            CRMComponent(
                component_type="session_checkpoint_list",
                component_id=f"session-checkpoints-{session_id}",
                title="本轮节点",
                props={"items": checkpoints},
            ),
        ],
    )


def approve_memory_suggestion(suggestion_id: int, *, actor: RequestActor) -> ActionMutationResponse:
    with get_connection() as connection:
        suggestion = update_memory_suggestion_status(connection, suggestion_id, status="approved")
        if suggestion is None:
            raise KeyError(str(suggestion_id))
        add_customer_memory_note(
            connection,
            str(suggestion["customer_id"]),
            str(suggestion["note_type"]),
            str(suggestion["content"]),
            source="approved-suggestion",
            confidence=str(suggestion["confidence"]),
            pinned=False,
        )
        update_customer_memory_fact_status(
            connection,
            customer_id=str(suggestion["customer_id"]),
            note_source=str(suggestion["content"]),
            source_session_id=str(suggestion.get("source_session_id") or ""),
            from_status="pending",
            to_status="approved",
            confirmed_by=actor.advisor_id,
        )
        related_session_ids = find_related_session_ids(
            connection,
            customer_id=str(suggestion["customer_id"]),
            session_id=str(suggestion.get("source_session_id") or ""),
        )
        bump_session_state_versions(connection, related_session_ids)
        session_meta = _build_mutation_session_meta(connection, related_session_ids)
        add_audit_event(
            connection,
            advisor_id=actor.advisor_id,
            store_id=actor.store_id,
            action_type="approve_memory_suggestion",
            entity_type="memory_suggestion",
            entity_id=str(suggestion_id),
            session_id=str(session_meta.get("session_id") or ""),
            before_summary=str(suggestion.get("status") or "pending"),
            after_summary="approved",
        )

    _invalidate_cache_for_sessions(related_session_ids)

    return ActionMutationResponse(
        entity_id=str(suggestion_id),
        status="approved",
        message="已转为长期记录，后续推荐会纳入这条信息。",
        session_meta=session_meta,
        updated_component=_build_action_result_notice_component(
            title="客户记录已确认",
            message="这条观察已进入稳定记录，后续推荐与维护建议会优先参考。",
            status="success",
        ),
    )


def reject_memory_suggestion(suggestion_id: int, *, actor: RequestActor) -> ActionMutationResponse:
    with get_connection() as connection:
        suggestion = update_memory_suggestion_status(connection, suggestion_id, status="rejected")
        if suggestion is None:
            raise KeyError(str(suggestion_id))
        update_customer_memory_fact_status(
            connection,
            customer_id=str(suggestion["customer_id"]),
            note_source=str(suggestion["content"]),
            source_session_id=str(suggestion.get("source_session_id") or ""),
            from_status="pending",
            to_status="rejected",
            confirmed_by=actor.advisor_id,
        )
        related_session_ids = find_related_session_ids(
            connection,
            customer_id=str(suggestion["customer_id"]),
            session_id=str(suggestion.get("source_session_id") or ""),
        )
        bump_session_state_versions(connection, related_session_ids)
        session_meta = _build_mutation_session_meta(connection, related_session_ids)
        add_audit_event(
            connection,
            advisor_id=actor.advisor_id,
            store_id=actor.store_id,
            action_type="reject_memory_suggestion",
            entity_type="memory_suggestion",
            entity_id=str(suggestion_id),
            session_id=str(session_meta.get("session_id") or ""),
            before_summary=str(suggestion.get("status") or "pending"),
            after_summary="rejected",
        )

    _invalidate_cache_for_sessions(related_session_ids)

    return ActionMutationResponse(
        entity_id=str(suggestion_id),
        status="rejected",
        message="已忽略这条待确认记录，不会写入长期记忆。",
        session_meta=session_meta,
        updated_component=_build_action_result_notice_component(
            title="待确认记录已忽略",
            message="这条观察不会进入稳定记录，后续推荐也不会继续引用。",
            status="info",
        ),
    )
