from app.services.guardrails import evaluate_message


def test_guardrails_allow_sales_domain_queries() -> None:
    result = evaluate_message("帮我找今天该优先跟进的重点会员", "缦序")
    assert result.allowed is True


def test_guardrails_reject_other_brands() -> None:
    result = evaluate_message("优衣库最近在卖什么爆款", "缦序")
    assert result.allowed is False
    assert "本品牌" in result.reason


def test_guardrails_reject_politics() -> None:
    result = evaluate_message("你怎么看最近的政治新闻", "缦序")
    assert result.allowed is False
