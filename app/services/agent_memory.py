from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.db import get_customer_memory_facts, get_customer_memory_notes, get_customer_memory_suggestions, get_session_state


REFERENCE_CUES = {
    "他",
    "她",
    "他的",
    "她的",
    "这个客户",
    "这位客户",
    "这位会员",
    "这个会员",
    "继续",
    "刚才",
    "上一个客户",
    "按她的喜好",
    "按他的喜好",
    "按这个来",
    "照这个来",
    "就按这个",
    "继续这个思路",
    "那就这么来",
}

MEMORY_UPDATE_CUES = {"记住", "补充", "更新", "备注", "以后按", "以后就按", "客户备注"}
MAINTENANCE_CUES = {"维护", "维护关系", "客户关系", "维系", "经营关系", "关怀", "唤醒", "修复关系"}
CATEGORY_TERMS = ["西装", "衬衫", "针织", "风衣", "半裙", "裙子", "连衣裙", "牛仔", "外套", "夹克"]
COLOR_TERMS = ["象牙白", "石墨灰", "雾蓝", "栗棕", "橄榄绿", "燕麦色"]
CATEGORY_NORMALIZATION = {"裙子": "半裙", "夹克": "外套"}
SUGGESTION_CUES = {"好像", "最近", "似乎", "感觉", "看来", "偏", "更偏", "常穿", "经常", "留意到", "在看"}


@dataclass(frozen=True)
class ResolvedTurnContext:
    active_customer_id: str | None
    active_customer_name: str
    reused_from_session: bool
    resolution_confidence: str
    session_state: dict


@dataclass(frozen=True)
class LayeredMemoryBundle:
    long_term_notes: list[dict]
    session_notes: list[dict]
    long_term_facts: list[dict]
    session_facts: list[dict]
    working_memory_summary: str


def should_reuse_active_customer(message: str) -> bool:
    return any(cue in message for cue in REFERENCE_CUES)


def is_relationship_maintenance_request(message: str) -> bool:
    return any(cue in message for cue in MAINTENANCE_CUES)


def is_memory_update_request(message: str) -> bool:
    return any(cue in message for cue in MEMORY_UPDATE_CUES)


def resolve_turn_context(
    connection,
    session_id: str,
    message: str,
    named_customer_ids: list[str],
    customer_lookup: dict[str, str],
) -> ResolvedTurnContext:
    state = get_session_state(connection, session_id)
    if named_customer_ids:
        customer_id = named_customer_ids[0]
        return ResolvedTurnContext(
            active_customer_id=customer_id,
            active_customer_name=customer_lookup.get(customer_id, ""),
            reused_from_session=False,
            resolution_confidence="high",
            session_state=state,
        )

    active_customer_id = state.get("active_customer_id")
    if active_customer_id and should_reuse_active_customer(message):
        return ResolvedTurnContext(
            active_customer_id=active_customer_id,
            active_customer_name=str(state.get("active_customer_name", "")),
            reused_from_session=True,
            resolution_confidence="medium",
            session_state=state,
        )

    return ResolvedTurnContext(
        active_customer_id=None,
        active_customer_name="",
        reused_from_session=False,
        resolution_confidence="low",
        session_state=state,
    )


def build_customer_lookup(connection, customer_ids: list[str]) -> dict[str, str]:
    if not customer_ids:
        return {}
    placeholders = ",".join("?" for _ in customer_ids)
    rows = connection.execute(
        f"SELECT id, name FROM customers WHERE id IN ({placeholders})",
        tuple(customer_ids),
    ).fetchall()
    return {str(row["id"]): str(row["name"]) for row in rows}


def get_customer_memory_bundle(connection, customer_id: str) -> dict:
    customer_row = connection.execute(
        """
        SELECT id, name, tier, style_profile, preferred_channel, preferred_colors, preferred_categories, note
        FROM customers
        WHERE id = ?
        """,
        (customer_id,),
    ).fetchone()
    if customer_row is None:
        return {}

    interaction_rows = connection.execute(
        """
        SELECT channel, summary, created_at
        FROM interaction_logs
        WHERE customer_id = ?
        ORDER BY created_at DESC
        LIMIT 3
        """,
        (customer_id,),
    ).fetchall()
    notes = get_customer_memory_notes(connection, customer_id, limit=4)
    facts = get_customer_memory_facts(connection, customer_id, statuses=["confirmed", "approved"], limit=12)

    return {
        "customer": dict(customer_row),
        "preferred_colors": json.loads(customer_row["preferred_colors"]),
        "preferred_categories": json.loads(customer_row["preferred_categories"]),
        "interaction_logs": [dict(row) for row in interaction_rows],
        "memory_notes": notes,
        "memory_facts": facts,
    }


def get_layered_memory_bundle(connection, customer_id: str, session_id: str, working_memory_summary: str = "") -> LayeredMemoryBundle:
    long_term_notes = get_customer_memory_notes(connection, customer_id, limit=6)
    session_notes = get_customer_memory_suggestions(connection, customer_id, limit=6, session_id=session_id)
    long_term_facts = get_customer_memory_facts(connection, customer_id, statuses=["confirmed", "approved"], limit=16)
    session_facts = get_customer_memory_facts(connection, customer_id, statuses=["pending"], limit=16)
    return LayeredMemoryBundle(
        long_term_notes=long_term_notes,
        session_notes=session_notes,
        long_term_facts=long_term_facts,
        session_facts=session_facts,
        working_memory_summary=working_memory_summary,
    )


def extract_memory_facts(note: str) -> list[dict]:
    if not note:
        return []

    facts: list[dict] = []
    lowered = note.strip()
    qualifiers = [token for token in ["轻薄", "通勤", "极简", "利落", "显瘦", "显高"] if token in lowered]
    qualifier = "、".join(qualifiers[:2])

    for term in CATEGORY_TERMS:
        normalized = CATEGORY_NORMALIZATION.get(term, term)
        if term not in lowered:
            continue
        if any(prefix in lowered for prefix in [f"不喜欢{term}", f"别推{term}", f"不要{term}", f"少推{term}", f"不太想穿{term}"]):
            facts.append(
                {
                    "dimension": "category_preference",
                    "value": normalized,
                    "polarity": "negative",
                    "qualifier": qualifier,
                }
            )
            continue
        if any(prefix in lowered for prefix in [f"喜欢{term}", f"更喜欢{term}", f"多推{term}", f"优先{term}", f"偏{term}", f"更偏{term}"]):
            facts.append(
                {
                    "dimension": "category_preference",
                    "value": normalized,
                    "polarity": "positive",
                    "qualifier": qualifier,
                }
            )

    for term in COLOR_TERMS:
        if term not in lowered:
            continue
        if any(prefix in lowered for prefix in [f"不喜欢{term}", f"不要{term}", f"少推{term}"]):
            facts.append(
                {
                    "dimension": "color_preference",
                    "value": term,
                    "polarity": "negative",
                    "qualifier": qualifier,
                }
            )
            continue
        if any(prefix in lowered for prefix in [f"喜欢{term}", f"更喜欢{term}", f"多推{term}", f"优先{term}", f"偏{term}", f"更偏{term}"]):
            facts.append(
                {
                    "dimension": "color_preference",
                    "value": term,
                    "polarity": "positive",
                    "qualifier": qualifier,
                }
            )

    for term in ["通勤", "上班", "约会", "度假"]:
        if term in lowered:
            polarity = "negative" if any(token in lowered for token in [f"不适合{term}", f"不喜欢{term}"]) else "positive"
            facts.append(
                {
                    "dimension": "scene_preference",
                    "value": term,
                    "polarity": polarity,
                    "qualifier": qualifier,
                }
            )

    for term in ["微信", "企微", "短信", "电话"]:
        if term in lowered and any(token in lowered for token in [f"优先{term}", f"更适合{term}", f"喜欢{term}联系", f"通过{term}"]):
            facts.append(
                {
                    "dimension": "service_channel",
                    "value": term,
                    "polarity": "positive",
                    "qualifier": qualifier,
                }
            )

    deduped: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    for fact in facts:
        signature = (
            str(fact["dimension"]),
            str(fact["value"]),
            str(fact["polarity"]),
            str(fact["qualifier"]),
        )
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(fact)
    return deduped


def extract_memory_note_update(message: str, customer_name: str = "") -> str | None:
    if not any(cue in message for cue in MEMORY_UPDATE_CUES):
        return None

    cleaned = message.replace(customer_name, "").strip(" ，。；:")
    cleaned = re.sub(r"^(记住|补充|更新|备注|以后按|以后就按|客户备注)", "", cleaned).strip(" ，。；:")
    if len(cleaned) < 6 and not any(term in cleaned for term in [*CATEGORY_TERMS, *COLOR_TERMS, "通勤", "轻薄", "显瘦", "极简", "利落"]):
        return None
    return cleaned[:140]


def extract_memory_suggestion(message: str, customer_name: str = "") -> str | None:
    if is_memory_update_request(message):
        return None
    if not any(cue in message for cue in SUGGESTION_CUES):
        return None

    cleaned = message.replace(customer_name, "").strip(" ，。；:")
    cleaned = cleaned.replace("她", "").replace("他", "").replace("这个客户", "").replace("这位客户", "")
    cleaned = cleaned.strip(" ，。；:")
    if len(cleaned) < 8:
        return None

    if not any(term in cleaned for term in [*CATEGORY_TERMS, *COLOR_TERMS, "通勤", "轻薄", "显瘦", "极简", "利落"]):
        return None

    return cleaned[:140]


def extract_preference_signals(memory_bundle: dict) -> dict:
    positive_categories = set(memory_bundle.get("preferred_categories", []))
    positive_colors = set(memory_bundle.get("preferred_colors", []))
    negative_categories: set[str] = set()
    negative_colors: set[str] = set()

    for note in memory_bundle.get("memory_notes", []):
        content = str(note.get("content", ""))
        for term in CATEGORY_TERMS:
            normalized = CATEGORY_NORMALIZATION.get(term, term)
            if term in content:
                negative_hit = any(prefix in content for prefix in [f"不喜欢{term}", f"别推{term}", f"不要{term}", f"少推{term}"])
                positive_hit = any(prefix in content for prefix in [f"喜欢{term}", f"更喜欢{term}", f"多推{term}", f"优先{term}"])
                if negative_hit:
                    negative_categories.add(normalized)
                if positive_hit and not negative_hit:
                    positive_categories.add(normalized)

        for term in COLOR_TERMS:
            if term in content:
                negative_hit = any(prefix in content for prefix in [f"不喜欢{term}", f"不要{term}", f"少推{term}"])
                positive_hit = any(prefix in content for prefix in [f"喜欢{term}", f"更喜欢{term}", f"多推{term}", f"优先{term}"])
                if negative_hit:
                    negative_colors.add(term)
                if positive_hit and not negative_hit:
                    positive_colors.add(term)

    for fact in memory_bundle.get("memory_facts", []):
        dimension = str(fact.get("dimension", ""))
        polarity = str(fact.get("polarity", ""))
        value = str(fact.get("value", ""))
        if dimension == "category_preference":
            if polarity == "negative":
                negative_categories.add(value)
                positive_categories.discard(value)
            elif polarity == "positive" and value not in negative_categories:
                positive_categories.add(value)
        if dimension == "color_preference":
            if polarity == "negative":
                negative_colors.add(value)
                positive_colors.discard(value)
            elif polarity == "positive" and value not in negative_colors:
                positive_colors.add(value)

    return {
        "positive_categories": positive_categories,
        "positive_colors": positive_colors,
        "negative_categories": negative_categories,
        "negative_colors": negative_colors,
    }


def detect_memory_conflict(note: str, memory_bundle: dict) -> str | None:
    if not note:
        return None

    content = str(note)
    long_term_notes = memory_bundle.get("memory_notes", []) if memory_bundle else []
    positive_categories: set[str] = set()
    positive_colors: set[str] = set()
    negative_categories: set[str] = set()
    negative_colors: set[str] = set()
    for category in memory_bundle.get("preferred_categories", []) if memory_bundle else []:
        positive_categories.add(str(category))
    for color in memory_bundle.get("preferred_colors", []) if memory_bundle else []:
        positive_colors.add(str(color))

    for note_item in long_term_notes:
        note_content = str(note_item.get("content", ""))
        for term in CATEGORY_TERMS:
            normalized = CATEGORY_NORMALIZATION.get(term, term)
            if term in note_content:
                if any(prefix in note_content for prefix in [f"不喜欢{term}", f"别推{term}", f"不要{term}", f"少推{term}", f"不太想穿{term}"]):
                    negative_categories.add(normalized)
                if any(prefix in note_content for prefix in [f"喜欢{term}", f"更喜欢{term}", f"多推{term}", f"优先{term}", "偏"]) and normalized not in negative_categories:
                    positive_categories.add(normalized)
        for term in COLOR_TERMS:
            if term in note_content:
                if any(prefix in note_content for prefix in [f"不喜欢{term}", f"不要{term}", f"少推{term}"]):
                    negative_colors.add(term)
                if any(prefix in note_content for prefix in [f"喜欢{term}", f"更喜欢{term}", f"多推{term}", f"优先{term}"]):
                    positive_colors.add(term)

    for fact in memory_bundle.get("memory_facts", []) if memory_bundle else []:
        dimension = str(fact.get("dimension", ""))
        value = str(fact.get("value", ""))
        polarity = str(fact.get("polarity", ""))
        if dimension == "category_preference":
            if polarity == "negative":
                negative_categories.add(value)
                positive_categories.discard(value)
            elif polarity == "positive" and value not in negative_categories:
                positive_categories.add(value)
        if dimension == "color_preference":
            if polarity == "negative":
                negative_colors.add(value)
                positive_colors.discard(value)
            elif polarity == "positive" and value not in negative_colors:
                positive_colors.add(value)

    for term in CATEGORY_TERMS:
        normalized = CATEGORY_NORMALIZATION.get(term, term)
        if term not in content:
            continue
        negative_hit = any(prefix in content for prefix in [f"不喜欢{term}", f"别推{term}", f"不要{term}", f"少推{term}"])
        positive_hit = any(prefix in content for prefix in [f"喜欢{term}", f"更喜欢{term}", f"多推{term}", f"优先{term}"])
        if negative_hit:
            if normalized in positive_categories:
                return f"历史记录里该客户对{normalized}是正向偏好，本轮新信息需要先确认。"
        if positive_hit and not negative_hit:
            if normalized in negative_categories:
                return f"历史记录里该客户对{normalized}有明确禁忌，本轮新信息需要先确认。"

    for term in COLOR_TERMS:
        if term not in content:
            continue
        negative_hit = any(prefix in content for prefix in [f"不喜欢{term}", f"不要{term}", f"少推{term}"])
        positive_hit = any(prefix in content for prefix in [f"喜欢{term}", f"更喜欢{term}", f"多推{term}", f"优先{term}"])
        if negative_hit:
            if term in positive_colors:
                return f"历史记录里该客户偏好{term}，本轮新信息需要先确认。"
        if positive_hit and not negative_hit:
            if term in negative_colors:
                return f"历史记录里该客户对{term}是负向偏好，本轮新信息需要先确认。"

    return None
