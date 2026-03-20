from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from app.config import get_app_settings
from app.db import add_turn, ensure_session, get_connection, get_recent_turn_summaries, row_to_dict
from app.schemas import CRMAction, CRMChatResponse, CRMComponent, CRMMessage, EntityDetailResponse, TaskCompleteResponse
from app.services.guardrails import evaluate_message
from app.services.llm_adapter import generate_assistant_brief, generate_message_draft


SUPPORTED_ACTIONS = ["open_customer", "open_product", "open_task", "complete_task"]
CONTEXT_VERSION = "crm-v1"
RESPONSE_CACHE: dict[tuple[str, str], CRMChatResponse] = {}


def get_bootstrap_payload() -> dict:
    settings = get_app_settings()
    with get_connection() as connection:
        pending = connection.execute(
            "SELECT COUNT(*) FROM follow_up_tasks WHERE status = 'open'"
        ).fetchone()[0]
    return {
        "advisor_name": settings.advisor_name,
        "store_name": settings.store_name,
        "brand_name": settings.brand_name,
        "pending_task_count": pending,
        "quick_prompts": [
            "帮我找今天该优先跟进但还没联系的高净值客户",
            "给偏好通勤西装的客户挑 3 款本周有货的单品",
            "把今天到期还没完成的回访任务按优先级排一下",
        ],
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


def _query_customer_candidates(connection, message: str, limit: int = 4) -> list[dict]:
    rows = connection.execute(
        """
        SELECT c.*, MIN(t.due_date) AS due_date, MAX(t.priority) AS task_priority, t.id AS task_id
        FROM customers c
        LEFT JOIN follow_up_tasks t
          ON c.id = t.customer_id AND t.status = 'open'
        GROUP BY c.id
        """
    ).fetchall()
    ranked = []
    for row in rows:
        customer = dict(row)
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
    limit: int = 4,
    *,
    category_hint: str = "",
    season_hint: str = "",
    query_terms: list[str] | None = None,
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
        haystack = " ".join(
            [
                product["name"],
                product["category"],
                product["subcategory"],
                product["collection_name"],
                product["summary"],
                product["color"],
                " ".join(json.loads(product["style_tags"])),
            ]
        )

        score = product["store_stock"] * 2 + product["warehouse_stock"]
        if category_hint and product["category"] == category_hint:
            score += 18
        if season_hint and season_hint in {"夏天", "春天"} and "春夏" in product["collection_name"]:
            score += 10
        if "夏天" in message and any(token in haystack for token in ["春夏", "轻", "通勤"]):
            score += 8

        for term in terms:
            if term and term in haystack:
                score += 6

        if "衣服" in message and product["category"] in {"西装", "衬衫", "针织", "风衣", "半裙", "连衣裙", "牛仔", "外套"}:
            score += 4
        ranked.append((score, product))

    ranked.sort(key=lambda item: (item[0], item[1]["price"]), reverse=True)
    items = []
    for _, product in ranked[:limit]:
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
                "store_stock": product["store_stock"],
                "warehouse_stock": product["warehouse_stock"],
            }
        )
    return items


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


def _build_trace_components(intent_label: str, entity_count: int) -> CRMComponent:
    return CRMComponent(
        component_type="trace_timeline",
        component_id=f"trace-{uuid.uuid4().hex[:8]}",
        title="处理轨迹",
        props={
            "items": [
                {"label": "识别需求范围", "detail": f"归类为 {intent_label}"},
                {"label": "检索门店数据", "detail": f"命中 {entity_count} 条候选记录"},
                {"label": "整理可执行建议", "detail": "输出客户、商品、任务和沟通建议"},
            ]
        },
    )


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
    )
    return CRMChatResponse(
        session_id=session_id,
        messages=[
            CRMMessage(
                message_id=f"user-{uuid.uuid4().hex[:8]}",
                role="user",
                text=message,
                created_at=_now(),
            ),
            assistant_message,
        ],
        ui_schema=assistant_message.ui_schema,
        supported_actions=SUPPORTED_ACTIONS,
        safety_status="rejected",
        context_version=CONTEXT_VERSION,
    )


def send_chat(message: str, session_id: str = None) -> CRMChatResponse:
    settings = get_app_settings()
    current_session_id = session_id or f"s_{uuid.uuid4().hex[:10]}"
    normalized = _normalize_message(message)

    cached = RESPONSE_CACHE.get((current_session_id, normalized))
    if cached:
        return cached.model_copy(deep=True)

    guardrail = evaluate_message(message, settings.brand_name)
    with get_connection() as connection:
        ensure_session(connection, current_session_id, settings.advisor_name, settings.store_name)
        if not guardrail.allowed:
            response = _build_rejection_response(message, current_session_id, guardrail.reason, guardrail.examples)
            add_turn(connection, current_session_id, "user", message, f"拒绝：{message[:48]}")
            add_turn(connection, current_session_id, "assistant", guardrail.reason, guardrail.reason)
            RESPONSE_CACHE[(current_session_id, normalized)] = response.model_copy(deep=True)
            return response

        add_turn(connection, current_session_id, "user", message, message[:80])
        summaries = get_recent_turn_summaries(connection, current_session_id)

        customer_candidates = (
            _query_customer_candidates(connection, message, limit=guardrail.requested_count)
            if guardrail.query_customers
            else []
        )
        products = (
            _query_products(
                connection,
                message,
                limit=guardrail.requested_count,
                category_hint=guardrail.category_hint,
                season_hint=guardrail.season_hint,
                query_terms=guardrail.query_terms or guardrail.style_terms,
            )
            if guardrail.query_products or customer_candidates
            else []
        )
        tasks = _query_tasks(connection, limit=guardrail.requested_count if guardrail.query_tasks else 0) if guardrail.query_tasks else []

        components: list[CRMComponent] = []
        intent_label = guardrail.intent_label

        if customer_candidates:
            components.append(
                CRMComponent(
                    component_type="customer_list",
                    component_id=f"customers-{uuid.uuid4().hex[:8]}",
                    title="建议优先跟进客户",
                    props={"items": customer_candidates},
                    actions=[],
                )
            )
        if products:
            components.append(
                CRMComponent(
                    component_type="product_grid",
                    component_id=f"products-{uuid.uuid4().hex[:8]}",
                    title="可直接推荐的门店单品" if not guardrail.season_hint else f"{guardrail.season_hint}可优先推荐的门店单品",
                    props={"items": products[: guardrail.requested_count]},
                )
            )
        if tasks:
            components.append(
                CRMComponent(
                    component_type="task_list",
                    component_id=f"tasks-{uuid.uuid4().hex[:8]}",
                    title="待处理任务",
                    props={"items": tasks[: guardrail.requested_count]},
                )
            )

        top_customer = customer_candidates[0] if customer_candidates else None
        recommended_product_names = [item["name"] for item in products[:3]]
        if top_customer:
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
            )
            components.append(
                CRMComponent(
                    component_type="message_draft",
                    component_id=f"draft-{uuid.uuid4().hex[:8]}",
                    title="建议沟通话术",
                    props={"text": draft_text},
                )
            )

        summary_seed = (
            f"客户 {len(customer_candidates)} 人，商品 {len(products)} 款，任务 {len(tasks)} 条。"
            f" 最近上下文：{'；'.join(summaries[-3:])[:180]}"
        )
        fallback_summary = "已按门店现有客户、商品和任务数据整理出一组可直接执行的跟进建议。"
        summary_text, _ = generate_assistant_brief(intent_label, message, summary_seed, fallback_summary)
        components.append(_build_trace_components(intent_label, len(customer_candidates) + len(products) + len(tasks)))

        assistant_message = CRMMessage(
            message_id=f"assistant-{uuid.uuid4().hex[:8]}",
            role="assistant",
            text=summary_text,
            created_at=_now(),
            ui_schema=components,
        )
        response = CRMChatResponse(
            session_id=current_session_id,
            messages=[
                CRMMessage(
                    message_id=f"user-{uuid.uuid4().hex[:8]}",
                    role="user",
                    text=message,
                    created_at=_now(),
                ),
                assistant_message,
            ],
            ui_schema=components,
            supported_actions=SUPPORTED_ACTIONS,
            safety_status="allowed",
            context_version=CONTEXT_VERSION,
        )
        add_turn(connection, current_session_id, "assistant", summary_text, summary_text[:80])

    RESPONSE_CACHE[(current_session_id, normalized)] = response.model_copy(deep=True)
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


def complete_task(task_id: str) -> TaskCompleteResponse:
    with get_connection() as connection:
        row = row_to_dict(
            connection.execute(
                """
                SELECT t.*, c.name AS customer_name
                FROM follow_up_tasks t
                JOIN customers c ON c.id = t.customer_id
                WHERE t.id = ?
                """,
                (task_id,),
            ).fetchone()
        )
        if row is None:
            raise KeyError(task_id)
        connection.execute("UPDATE follow_up_tasks SET status = 'done' WHERE id = ?", (task_id,))
        connection.commit()

    component = CRMComponent(
        component_type="task_card",
        component_id=f"task-complete-{task_id}",
        title=row["task_type"],
        props={
            "id": task_id,
            "customer_name": row["customer_name"],
            "priority": row["priority"],
            "due_date": row["due_date"],
            "status": "done",
            "reason": row["reason"],
        },
        actions=[],
    )
    return TaskCompleteResponse(
        task_id=task_id,
        status="done",
        message="任务已标记完成，并同步更新到工作台。",
        updated_component=component,
    )
