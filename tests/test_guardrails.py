import os

from app.services import guardrails as guardrails_module
from app.services.guardrails import evaluate_message


os.environ["MODEL_PROVIDER"] = "mock"
os.environ["MODEL_API_KEY"] = ""


def test_guardrails_allow_sales_domain_queries() -> None:
    result = evaluate_message("帮我找今天该优先跟进的重点会员", "缦序")
    assert result.allowed is True


def test_guardrails_allow_semantic_product_query() -> None:
    result = evaluate_message("找5件适合夏天穿的衣服", "缦序")
    assert result.allowed is True
    assert result.intent == "product_recommendation"
    assert result.requested_count == 5
    assert result.season_hint == "夏天"


def test_guardrails_default_requested_count_respects_config(monkeypatch) -> None:
    monkeypatch.setenv("CRM_DEFAULT_RESULT_COUNT", "6")
    guardrails_module.INTENT_CACHE.clear()

    result = evaluate_message("帮我推荐几件适合通勤的衣服", "缦序")

    assert result.allowed is True
    assert result.intent == "product_recommendation"
    assert result.requested_count == 6


def test_guardrails_allow_relationship_maintenance_query() -> None:
    result = evaluate_message("我要维护一下乔安禾的客户关系", "缦序")
    assert result.allowed is True
    assert result.intent == "relationship_maintenance"


def test_guardrails_reject_other_brands() -> None:
    result = evaluate_message("优衣库最近在卖什么爆款", "缦序")
    assert result.allowed is False
    assert "本品牌" in result.reason


def test_guardrails_reject_politics() -> None:
    result = evaluate_message("你怎么看最近的政治新闻", "缦序")
    assert result.allowed is False


def test_guardrails_allow_category_direct_queries() -> None:
    result = evaluate_message("有哪些外套", "缦序")
    assert result.allowed is True
    assert result.intent == "product_recommendation"
    assert result.category_hint == "外套"


def test_guardrails_keep_explicit_sales_query_when_model_disagrees(monkeypatch) -> None:
    guardrails_module.INTENT_CACHE.clear()

    monkeypatch.setattr(
        guardrails_module,
        "classify_sales_intent",
        lambda message, brand_name: (
            {
                "domain": "out_of_scope",
                "intent": "unknown",
                "customer_context": False,
                "requested_count": 4,
                "category_hint": "",
                "season_hint": "",
                "style_terms": [],
                "query_terms": [],
                "reason": "misclassified",
                "confidence": "low",
            },
            "test-model",
        ),
    )

    result = evaluate_message("帮我给乔安禾发条消息", "缦序")
    assert result.allowed is True
    assert result.intent == "message_draft"
