from dataclasses import dataclass


ALLOWED_KEYWORDS = {
    "客户",
    "会员",
    "跟进",
    "任务",
    "库存",
    "有货",
    "商品",
    "单品",
    "推荐",
    "搭配",
    "话术",
    "回访",
    "到店",
    "上新",
    "西装",
    "衬衫",
    "针织",
    "风衣",
    "裙",
}

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


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str
    examples: list[str]


def evaluate_message(message: str, brand_name: str) -> GuardrailResult:
    lowered = message.lower()

    if any(keyword in lowered for keyword in OTHER_BRANDS if keyword != brand_name.lower()):
        return GuardrailResult(
            allowed=False,
            reason="当前工作台只支持本品牌门店客户、商品和任务范围内的问题。",
            examples=[
                "帮我找今天该优先跟进的重点客户",
                "推荐 3 款有现货的通勤单品",
                "整理今天到期的回访任务",
            ],
        )

    if any(keyword in message for keyword in BLOCKED_KEYWORDS):
        return GuardrailResult(
            allowed=False,
            reason="当前工作台不处理品牌外、政治或泛商业讨论，只支持导购业务问题。",
            examples=[
                "查看客户详情",
                "查询库存",
                "整理跟进建议",
            ],
        )

    if any(keyword in message for keyword in ALLOWED_KEYWORDS):
        return GuardrailResult(allowed=True, reason="allowed", examples=[])

    return GuardrailResult(
        allowed=False,
        reason="当前工作台只支持客户筛选、商品推荐、库存查询、任务处理和话术整理。",
        examples=[
            "找今天还没联系的高净值客户",
            "给偏好通勤风格的客户挑 3 款有货单品",
            "把今天到期的任务按优先级排一下",
        ],
    )
