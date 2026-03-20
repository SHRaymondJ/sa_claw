import os

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


def test_guardrails_reject_other_brands() -> None:
    result = evaluate_message("优衣库最近在卖什么爆款", "缦序")
    assert result.allowed is False
    assert "本品牌" in result.reason


def test_guardrails_reject_politics() -> None:
    result = evaluate_message("你怎么看最近的政治新闻", "缦序")
    assert result.allowed is False
