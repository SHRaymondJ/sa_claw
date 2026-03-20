from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.llm_adapter import classify_sales_intent


BLOCKED_KEYWORDS = {
    "政治",
    "政府",
    "总统",
    "主席",
    "战争",
    "选举",
    "股市",
    "融资",
    "宏观",
    "商业模式",
    "其他品牌",
}

OTHER_BRANDS = {
    "zara",
    "优衣库",
    "lululemon",
    "chanel",
    "gucci",
    "nike",
    "adidas",
    "太平鸟",
}

INTENT_CACHE: dict[tuple[str, str], "GuardrailResult"] = {}

PRODUCT_CUES = {
    "商品",
    "单品",
    "衣服",
    "穿搭",
    "穿",
    "适合",
    "推荐",
    "搭配",
    "look",
    "上新",
    "夏天",
    "夏季",
    "春天",
    "秋天",
    "冬天",
    "通勤",
    "上班",
    "约会",
    "度假",
    "显瘦",
    "显高",
    "小个子",
    "高个子",
    "轻薄",
    "透气",
    "凉快",
}

CUSTOMER_CUES = {
    "客户",
    "会员",
    "高净值",
    "未联系",
    "没联系",
    "未触达",
    "触达",
    "联系",
    "回访",
    "客群",
}

INVENTORY_CUES = {
    "库存",
    "现货",
    "有货",
    "补货",
    "尺码",
    "门店还有",
    "还能买",
}

TASK_CUES = {
    "任务",
    "待办",
    "到期",
    "优先级",
    "完成",
    "跟进",
    "处理",
}

SCRIPT_CUES = {
    "话术",
    "私聊",
    "微信",
    "怎么说",
    "发什么",
    "文案",
    "短信",
}

CATEGORY_HINTS = {
    "西装": "西装",
    "衬衫": "衬衫",
    "针织": "针织",
    "风衣": "风衣",
    "半裙": "半裙",
    "裙子": "半裙",
    "连衣裙": "连衣裙",
    "牛仔": "牛仔",
    "外套": "外套",
    "夹克": "外套",
    "上衣": "衬衫",
    "裤子": "牛仔",
    "衣服": "",
}

SEASON_HINTS = {
    "夏天": "夏天",
    "夏季": "夏天",
    "春夏": "夏天",
    "秋天": "秋天",
    "秋季": "秋天",
    "冬天": "冬天",
    "冬季": "冬天",
    "春天": "春天",
    "春季": "春天",
}

CHINESE_NUMERALS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str
    examples: list[str]
    intent: str = "unknown"
    intent_label: str = "未知需求"
    query_products: bool = False
    query_customers: bool = False
    query_tasks: bool = False
    requested_count: int = 4
    category_hint: str = ""
    season_hint: str = ""
    customer_context: bool = False
    style_terms: list[str] = field(default_factory=list)
    query_terms: list[str] = field(default_factory=list)
    confidence: str = "low"


def _extract_requested_count(message: str, default: int = 4) -> int:
    arabic = re.search(r"(\d+)\s*(件|款|个|套)", message)
    if arabic:
        return max(1, min(int(arabic.group(1)), 8))

    chinese = re.search(r"([一二两三四五六七八九十])\s*(件|款|个|套)", message)
    if chinese:
        return max(1, min(CHINESE_NUMERALS.get(chinese.group(1), default), 8))

    return default


def _match_hint(message: str, hints: dict[str, str]) -> str:
    for raw, normalized in hints.items():
        if raw in message:
            return normalized
    return ""


def _heuristic_classification(message: str) -> GuardrailResult:
    text = message.lower()
    quantity = _extract_requested_count(message)
    category_hint = _match_hint(message, CATEGORY_HINTS)
    season_hint = _match_hint(message, SEASON_HINTS)

    product_hits = sum(1 for cue in PRODUCT_CUES if cue in text or cue in message)
    customer_hits = sum(1 for cue in CUSTOMER_CUES if cue in message)
    inventory_hits = sum(1 for cue in INVENTORY_CUES if cue in message)
    task_hits = sum(1 for cue in TASK_CUES if cue in message)
    script_hits = sum(1 for cue in SCRIPT_CUES if cue in message)

    if inventory_hits and product_hits:
        intent = "inventory_lookup"
        intent_label = "库存查询"
    elif task_hits:
        intent = "task_management"
        intent_label = "任务处理"
    elif script_hits:
        intent = "message_draft"
        intent_label = "话术整理"
    elif product_hits:
        intent = "product_recommendation"
        intent_label = "商品推荐"
    elif customer_hits:
        intent = "customer_filter"
        intent_label = "客户筛选"
    else:
        return GuardrailResult(
            allowed=False,
            reason="当前工作台只支持客户筛选、商品推荐、库存查询、任务处理和话术整理。",
            examples=[
                "找今天还没联系的高净值客户",
                "给偏好通勤风格的客户挑 3 款有货单品",
                "把今天到期的任务按优先级排一下",
            ],
        )

    customer_context = customer_hits > 0
    style_terms = [
        term
        for term in ["通勤", "上班", "约会", "度假", "显瘦", "显高", "小个子", "轻薄", "透气", "凉快"]
        if term in message
    ]
    query_terms = [term for term in [category_hint, season_hint, *style_terms] if term]

    return GuardrailResult(
        allowed=True,
        reason="allowed",
        examples=[],
        intent=intent,
        intent_label=intent_label,
        query_products=intent in {"product_recommendation", "inventory_lookup"} or customer_context,
        query_customers=intent == "customer_filter" or customer_context,
        query_tasks=intent == "task_management",
        requested_count=quantity,
        category_hint=category_hint,
        season_hint=season_hint,
        customer_context=customer_context,
        style_terms=style_terms,
        query_terms=query_terms,
        confidence="medium",
    )


def _from_model_payload(payload: dict) -> GuardrailResult | None:
    domain = str(payload.get("domain", "")).strip().lower()
    intent = str(payload.get("intent", "")).strip().lower()
    confidence = str(payload.get("confidence", "low")).strip().lower() or "low"
    if domain not in {"sales", "out_of_scope"}:
        return None

    if domain == "out_of_scope" or intent == "unknown":
        return GuardrailResult(
            allowed=False,
            reason="当前工作台只支持客户筛选、商品推荐、库存查询、任务处理和话术整理。",
            examples=[
                "找今天还没联系的高净值客户",
                "给偏好通勤风格的客户挑 3 款有货单品",
                "把今天到期的任务按优先级排一下",
            ],
        )

    quantity = payload.get("requested_count", 4)
    if not isinstance(quantity, int):
        quantity = 4

    category_hint = str(payload.get("category_hint", "")).strip()
    season_hint = str(payload.get("season_hint", "")).strip()
    style_terms = [str(item).strip() for item in payload.get("style_terms", []) if str(item).strip()]
    query_terms = [str(item).strip() for item in payload.get("query_terms", []) if str(item).strip()]
    customer_context = bool(payload.get("customer_context", False))

    intent_label_map = {
        "product_recommendation": "商品推荐",
        "customer_filter": "客户筛选",
        "inventory_lookup": "库存查询",
        "task_management": "任务处理",
        "message_draft": "话术整理",
    }
    if intent not in intent_label_map:
        return None

    return GuardrailResult(
        allowed=True,
        reason="allowed",
        examples=[],
        intent=intent,
        intent_label=intent_label_map[intent],
        query_products=intent in {"product_recommendation", "inventory_lookup"} or customer_context,
        query_customers=intent == "customer_filter" or customer_context,
        query_tasks=intent == "task_management",
        requested_count=max(1, min(quantity, 8)),
        category_hint=category_hint,
        season_hint=season_hint,
        customer_context=customer_context,
        style_terms=style_terms,
        query_terms=query_terms,
        confidence=confidence,
    )


def evaluate_message(message: str, brand_name: str) -> GuardrailResult:
    lowered = message.lower()
    cache_key = (brand_name.lower(), " ".join(lowered.split()))
    cached = INTENT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if any(keyword in lowered for keyword in OTHER_BRANDS if keyword != brand_name.lower()):
        result = GuardrailResult(
            allowed=False,
            reason="当前工作台只支持本品牌门店客户、商品和任务范围内的问题。",
            examples=[
                "帮我找今天该优先跟进的重点客户",
                "推荐 3 款有现货的通勤单品",
                "整理今天到期的回访任务",
            ],
        )
        INTENT_CACHE[cache_key] = result
        return result

    if any(keyword in message for keyword in BLOCKED_KEYWORDS):
        result = GuardrailResult(
            allowed=False,
            reason="当前工作台不处理品牌外、政治或泛商业讨论，只支持导购业务问题。",
            examples=[
                "查看客户详情",
                "查询库存",
                "整理跟进建议",
            ],
        )
        INTENT_CACHE[cache_key] = result
        return result

    payload, _ = classify_sales_intent(message, brand_name)
    if payload:
        model_result = _from_model_payload(payload)
        if model_result is not None:
            INTENT_CACHE[cache_key] = model_result
            return model_result

    heuristic_result = _heuristic_classification(message)
    INTENT_CACHE[cache_key] = heuristic_result
    return heuristic_result
