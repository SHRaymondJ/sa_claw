import os
import json

from fastapi.testclient import TestClient

from app.config import get_app_settings
from app.db import get_connection, init_db
from app.main import app
from app.services.crm_service import RESPONSE_CACHE


os.environ["MODEL_PROVIDER"] = "mock"
os.environ["MODEL_API_KEY"] = ""

init_db()
client = TestClient(app)
SETTINGS = get_app_settings()
AUTH_HEADERS = {
    "X-Advisor-Id": SETTINGS.advisor_id,
    "X-Store-Id": SETTINGS.store_id,
}


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bootstrap_and_chat_flow() -> None:
    bootstrap_response = client.get("/api/crm/bootstrap")
    assert bootstrap_response.status_code == 200
    payload = bootstrap_response.json()
    assert "advisor_name" in payload
    assert payload["pending_task_count"] >= 0
    assert payload["preview_customer_id"]

    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "帮我找今天该优先跟进但还没联系的高净值客户"},
    )
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert data["safety_status"] == "allowed"
    component_types = [component["component_type"] for component in data["ui_schema"]]
    assert "customer_list" in component_types
    assert "message_draft" not in component_types


def test_runtime_identity_defaults_are_neutral(monkeypatch) -> None:
    monkeypatch.delenv("CRM_BRAND_NAME", raising=False)
    monkeypatch.delenv("CRM_ADVISOR_NAME", raising=False)
    monkeypatch.delenv("CRM_STORE_NAME", raising=False)
    monkeypatch.delenv("CRM_ADVISOR_ID", raising=False)
    monkeypatch.delenv("CRM_STORE_ID", raising=False)

    settings = get_app_settings()

    assert settings.brand_name == ""
    assert settings.advisor_name == ""
    assert settings.store_name == ""
    assert settings.advisor_id == "advisor-default"
    assert settings.store_id == "store-default"


def test_chat_endpoint_respects_configured_rate_limit(monkeypatch) -> None:
    monkeypatch.setenv("CRM_CHAT_RATE_LIMIT", "2")
    monkeypatch.setenv("CRM_CHAT_RATE_WINDOW_SECONDS", "60")

    headers = {
        "X-Advisor-Id": "advisor-rate-limit-case",
        "X-Store-Id": SETTINGS.store_id,
    }
    payload = {
        "session_id": "session-rate-limit-case",
        "message": "帮我找今天该优先跟进但还没联系的高净值客户",
    }

    first = client.post("/api/crm/chat/send", json=payload, headers=headers)
    second = client.post("/api/crm/chat/send", json=payload, headers=headers)
    third = client.post("/api/crm/chat/send", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "rate limit exceeded"


def test_mutation_endpoint_respects_configured_rate_limit(monkeypatch) -> None:
    monkeypatch.setenv("CRM_MUTATION_RATE_LIMIT", "2")
    monkeypatch.setenv("CRM_MUTATION_RATE_WINDOW_SECONDS", "60")

    headers = {
        "X-Advisor-Id": "advisor-mutation-rate-limit-case",
        "X-Store-Id": SETTINGS.store_id,
    }

    first = client.post("/api/crm/tasks/T404-A/complete", headers=headers)
    second = client.post("/api/crm/tasks/T404-B/complete", headers=headers)
    third = client.post("/api/crm/tasks/T404-C/complete", headers=headers)

    assert first.status_code == 404
    assert second.status_code == 404
    assert third.status_code == 429
    assert third.json()["detail"] == "rate limit exceeded"


def test_semantic_product_query_flow() -> None:
    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "找5件适合夏天穿的衣服"},
    )
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert data["safety_status"] == "allowed"
    product_component = next(component for component in data["ui_schema"] if component["component_type"] == "product_grid")
    assert len(product_component["props"]["items"]) == 5
    assert "夏天" in product_component["title"]
    assert product_component["props"]["items"][0]["match_reason"]
    assert product_component["props"]["items"][0]["display_tags"]


def test_customer_inventory_query_shows_overview_and_sample_list() -> None:
    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "现在有哪些客户"},
    )
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert data["safety_status"] == "allowed"
    component_types = [component["component_type"] for component in data["ui_schema"]]
    assert component_types[:2] == ["customer_overview", "workflow_checkpoint"]
    assert "customer_list" in component_types
    summary = data["messages"][-1]["text"]
    assert "共有" in summary
    assert "先展示" in summary

    overview_component = next(
        component for component in data["ui_schema"] if component["component_type"] == "customer_overview"
    )
    assert overview_component["props"]["total_customers"] > overview_component["props"]["sample_limit"]

    sample_component = next(component for component in data["ui_schema"] if component["component_type"] == "customer_list")
    assert len(sample_component["props"]["items"]) == overview_component["props"]["sample_limit"]


def test_customer_inventory_query_respects_configured_sample_limit(monkeypatch) -> None:
    RESPONSE_CACHE.clear()
    monkeypatch.setenv("CRM_CUSTOMER_SAMPLE_LIMIT", "6")

    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "现在有哪些客户"},
    )

    assert chat_response.status_code == 200
    data = chat_response.json()
    overview_component = next(
        component for component in data["ui_schema"] if component["component_type"] == "customer_overview"
    )
    sample_component = next(component for component in data["ui_schema"] if component["component_type"] == "customer_list")
    assert overview_component["props"]["sample_limit"] == 6
    assert len(sample_component["props"]["items"]) == 6


def test_category_inventory_query_shows_category_overview_only() -> None:
    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "现在有哪些品类"},
    )
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert data["safety_status"] == "allowed"
    component_types = [component["component_type"] for component in data["ui_schema"]]
    assert component_types == ["category_overview"]
    assert "共有" in data["messages"][-1]["text"]
    assert "product_grid" not in component_types

    overview_component = data["ui_schema"][0]
    assert overview_component["props"]["total_categories"] == len(overview_component["props"]["items"])


def test_category_keyword_queries_are_allowed() -> None:
    for query in ["有哪些连衣裙", "有哪些外套"]:
        chat_response = client.post("/api/crm/chat/send", json={"message": query})
        assert chat_response.status_code == 200
        data = chat_response.json()
        assert data["safety_status"] == "allowed"
        assert "product_grid" in [component["component_type"] for component in data["ui_schema"]]


def test_named_customer_message_draft_is_allowed() -> None:
    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "帮我给乔安禾发条消息"},
    )
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert data["safety_status"] == "allowed"
    component_types = [component["component_type"] for component in data["ui_schema"]]
    assert component_types[:2] == ["customer_spotlight", "workflow_checkpoint"]
    assert "message_draft" in component_types


def test_named_customer_preference_query_returns_profile_components() -> None:
    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "乔知夏喜欢什么"},
    )
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert data["safety_status"] == "allowed"
    component_types = [component["component_type"] for component in data["ui_schema"]]
    assert component_types[0] == "customer_spotlight"
    assert "detail_kv" in component_types
    assert "tag_group" in component_types
    assert "乔知夏" in data["messages"][-1]["text"]


def test_customer_tag_inventory_query_shows_tag_overview() -> None:
    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "我想看看客户标签"},
    )
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert data["safety_status"] == "allowed"
    assert [component["component_type"] for component in data["ui_schema"]] == ["tag_group"]
    assert "最常见" in data["messages"][-1]["text"]


def test_session_state_tracks_response_shape_and_entities() -> None:
    first = client.post(
        "/api/crm/chat/send",
        json={"message": "现在有哪些客户"},
    )
    assert first.status_code == 200
    session_id = first.json()["session_id"]

    session_detail = client.get(f"/api/crm/sessions/{session_id}")
    assert session_detail.status_code == 200
    detail_kv = next(
        component for component in session_detail.json()["ui_schema"] if component["component_type"] == "detail_kv"
    )
    labels = {item["label"]: item["value"] for item in detail_kv["props"]["items"]}
    assert labels["当前意图"] == "customer_filter"
    assert labels["当前模式"] == "看客户池"
    assert "customer_overview+workflow_checkpoint+customer_list" == labels["返回形态"]
    assert labels["最近实体"]
    assert labels["切换原因"]
    assert labels["工作记忆"]


def test_chat_response_exposes_session_snapshot_meta() -> None:
    response = client.post(
        "/api/crm/chat/send",
        json={"message": "乔知夏喜欢什么"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["question_type"] == "customer_insight"
    assert payload["meta"]["conversation_mode"] == "customer_insight"
    assert payload["meta"]["conversation_mode_label"] == "看客户画像"
    assert payload["meta"]["session_snapshot"]["active_customer_name"] == "乔知夏"
    assert payload["messages"][-1]["meta"]["status_hint"] == "看客户画像"


def test_switching_named_customers_does_not_leak_previous_preferences() -> None:
    first = client.post(
        "/api/crm/chat/send",
        json={"message": "乔安禾喜欢什么"},
    )
    assert first.status_code == 200
    first_payload = first.json()
    session_id = first_payload["session_id"]
    assert first_payload["ui_schema"][0]["props"]["item"]["name"] == "乔安禾"

    second = client.post(
        "/api/crm/chat/send",
        json={"session_id": session_id, "message": "乔知夏喜欢什么"},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["ui_schema"][0]["props"]["item"]["name"] == "乔知夏"
    summary_component = next(
        component for component in second_payload["ui_schema"] if component["component_type"] == "detail_kv"
    )
    values = {item["label"]: item["value"] for item in summary_component["props"]["items"]}
    assert "乔安禾" not in " ".join(values.values())


def test_follow_up_pronoun_reuses_active_customer_conservatively() -> None:
    first = client.post(
        "/api/crm/chat/send",
        json={"message": "我要维护一下乔安禾的客户关系"},
    )
    assert first.status_code == 200
    payload = first.json()
    session_id = payload["session_id"]

    second = client.post(
        "/api/crm/chat/send",
        json={"session_id": session_id, "message": "按她的喜好推荐维护关系的方式"},
    )
    assert second.status_code == 200
    follow_up = second.json()
    assert follow_up["ui_schema"][0]["props"]["item"]["name"] == "乔安禾"
    assert "customer_list" not in [component["component_type"] for component in follow_up["ui_schema"]]
    assert follow_up["meta"]["handoff_reason"]


def test_long_conversation_keeps_same_customer_across_five_turns() -> None:
    prompts = [
        "我要维护一下乔安禾的客户关系",
        "按她的喜好推荐维护关系的方式",
        "继续给她推荐一下",
        "帮我给她发条消息",
        "再总结一下她现在适合怎么维护",
    ]
    session_id = None
    for prompt in prompts:
        payload = {"message": prompt}
        if session_id:
            payload["session_id"] = session_id
        response = client.post("/api/crm/chat/send", json=payload)
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        assert data["meta"]["session_snapshot"]["active_customer_name"] == "乔安禾"

    final_detail = client.get(f"/api/crm/sessions/{session_id}")
    detail_kv = next(component for component in final_detail.json()["ui_schema"] if component["component_type"] == "detail_kv")
    labels = {item["label"]: item["value"] for item in detail_kv["props"]["items"]}
    assert labels["当前客户"] == "乔安禾"


def test_task_turn_clears_customer_focus_after_customer_conversation() -> None:
    first = client.post("/api/crm/chat/send", json={"message": "乔安禾喜欢什么"})
    session_id = first.json()["session_id"]

    second = client.post(
        "/api/crm/chat/send",
        json={"session_id": session_id, "message": "把今天到期还没完成的回访任务按优先级排一下"},
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["meta"]["conversation_mode"] == "task_management"
    assert payload["meta"]["session_snapshot"]["active_customer_name"] in {"", None}
    assert "task_list" in [component["component_type"] for component in payload["ui_schema"]]


def test_conflicting_memory_note_stays_pending_instead_of_overwriting_long_term_memory() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM customer_memory_notes
            WHERE customer_id IN (SELECT id FROM customers WHERE name = '乔安禾')
              AND source = 'advisor-chat'
            """
        )
        connection.execute(
            """
            DELETE FROM customer_memory_facts
            WHERE customer_id IN (SELECT id FROM customers WHERE name = '乔安禾')
              AND source_type IN ('advisor-chat', 'advisor-chat-conflict', 'advisor-observation', 'approved-suggestion')
            """
        )
        connection.commit()

    first = client.post("/api/crm/chat/send", json={"message": "乔安禾喜欢什么"})
    session_id = first.json()["session_id"]
    customer_id = first.json()["meta"]["session_snapshot"]["active_customer_id"]
    with get_connection() as connection:
        preferred_categories_raw = connection.execute(
            "SELECT preferred_categories FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
    assert preferred_categories_raw is not None
    preferred_category = json.loads(preferred_categories_raw["preferred_categories"])[0]

    conflict = client.post(
        "/api/crm/chat/send",
        json={"session_id": session_id, "message": f"记住她不喜欢{preferred_category}"},
    )
    assert conflict.status_code == 200
    payload = conflict.json()
    assert "待确认" in payload["messages"][-1]["text"]
    assert any(component["component_type"] == "memory_suggestions" for component in payload["ui_schema"])

    detail = client.get(f"/api/crm/customers/{customer_id}")
    assert detail.status_code == 200
    memory_briefs = next(component for component in detail.json()["ui_schema"] if component["component_type"] == "memory_briefs")
    assert not any(
        item["source"] == "导购补充" and preferred_category in item["content"] for item in memory_briefs["props"]["items"]
    )


def test_named_customer_product_query_is_compact() -> None:
    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "给乔知夏推荐一些产品，并且说明理由"},
    )
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert data["safety_status"] == "allowed"
    component_types = [component["component_type"] for component in data["ui_schema"]]
    assert component_types == ["customer_spotlight", "workflow_checkpoint", "product_grid"]
    spotlight = data["ui_schema"][0]
    assert spotlight["props"]["item"]["name"] == "乔知夏"
    workflow_component = data["ui_schema"][1]
    assert workflow_component["title"] == "本轮执行节奏"
    product_component = data["ui_schema"][2]
    assert "给乔知夏的推荐单品" == product_component["title"]
    assert product_component["props"]["items"][0]["match_reason"]
    names = [item["name"] for item in product_component["props"]["items"]]
    assert len(names) == len(set(names))
    assert len(data["messages"][-1]["text"]) <= 72


def test_repeat_query_preserves_product_entities_by_default() -> None:
    RESPONSE_CACHE.clear()

    first = client.post(
        "/api/crm/chat/send",
        json={"message": "给乔知夏推荐一些产品，并且说明理由"},
    )
    assert first.status_code == 200
    first_payload = first.json()
    session_id = first_payload["session_id"]
    first_grid = next(component for component in first_payload["ui_schema"] if component["component_type"] == "product_grid")
    first_ids = [item["id"] for item in first_grid["props"]["items"]]
    assert first_payload["meta"]["repeat_query_mode"] == "fresh"

    second = client.post(
        "/api/crm/chat/send",
        json={"session_id": session_id, "message": "给乔知夏推荐一些产品，并且说明理由"},
    )
    assert second.status_code == 200
    second_payload = second.json()
    second_grid = next(component for component in second_payload["ui_schema"] if component["component_type"] == "product_grid")
    second_ids = [item["id"] for item in second_grid["props"]["items"]]

    assert second_payload["meta"]["repeat_query_mode"] == "preserve"
    assert second_ids == first_ids


def test_repeat_query_diversifies_when_user_asks_for_another_batch() -> None:
    RESPONSE_CACHE.clear()

    first = client.post(
        "/api/crm/chat/send",
        json={"message": "找3件适合夏天穿的衣服"},
    )
    assert first.status_code == 200
    first_payload = first.json()
    session_id = first_payload["session_id"]
    first_grid = next(component for component in first_payload["ui_schema"] if component["component_type"] == "product_grid")
    first_ids = [item["id"] for item in first_grid["props"]["items"]]
    assert len(first_ids) == 3

    second = client.post(
        "/api/crm/chat/send",
        json={"session_id": session_id, "message": "换一批"},
    )
    assert second.status_code == 200
    second_payload = second.json()
    second_grid = next(component for component in second_payload["ui_schema"] if component["component_type"] == "product_grid")
    second_ids = [item["id"] for item in second_grid["props"]["items"]]

    assert second_payload["meta"]["repeat_query_mode"] == "diversify"
    assert len(second_ids) == 3
    assert second_ids != first_ids


def test_relationship_maintenance_uses_customer_memory_and_session_context() -> None:
    first = client.post(
        "/api/crm/chat/send",
        json={"message": "我要维护一下乔安禾的客户关系"},
    )
    assert first.status_code == 200
    payload = first.json()
    assert payload["safety_status"] == "allowed"
    assert payload["ui_schema"][0]["component_type"] == "customer_spotlight"
    assert payload["ui_schema"][0]["props"]["item"]["name"] == "乔安禾"
    assert payload["ui_schema"][1]["component_type"] == "workflow_checkpoint"
    assert payload["ui_schema"][2]["component_type"] == "relationship_plan"
    assert payload["ui_schema"][3]["component_type"] == "knowledge_briefs"
    assert payload["ui_schema"][4]["component_type"] == "product_grid"

    second = client.post(
        "/api/crm/chat/send",
        json={
            "session_id": payload["session_id"],
            "message": "你就按照他的喜好给我推荐维护关系的方式吧",
        },
    )
    assert second.status_code == 200
    follow_up = second.json()
    assert follow_up["safety_status"] == "allowed"
    assert follow_up["ui_schema"][0]["component_type"] == "customer_spotlight"
    assert follow_up["ui_schema"][0]["props"]["item"]["name"] == "乔安禾"
    assert follow_up["ui_schema"][1]["component_type"] == "workflow_checkpoint"
    assert follow_up["ui_schema"][2]["component_type"] == "relationship_plan"
    assert follow_up["ui_schema"][3]["component_type"] == "knowledge_briefs"
    assert "客户清单" not in [item["component_type"] for item in follow_up["ui_schema"]]


def test_relationship_maintenance_snapshot_matches_visible_product_count() -> None:
    RESPONSE_CACHE.clear()

    response = client.post(
        "/api/crm/chat/send",
        json={"message": "我要维护一下乔安禾的客户关系"},
    )
    assert response.status_code == 200
    payload = response.json()

    product_component = next(component for component in payload["ui_schema"] if component["component_type"] == "product_grid")
    visible_ids = [item["id"] for item in product_component["props"]["items"]]

    assert payload["meta"]["focus_scope"]["product_ids"] == visible_ids
    assert payload["meta"]["session_snapshot"]["last_entity_ids"][: 1 + len(visible_ids)] == [
        payload["ui_schema"][0]["props"]["item"]["id"],
        *visible_ids,
    ]


def test_workflow_checkpoint_note_limit_respects_config(monkeypatch) -> None:
    RESPONSE_CACHE.clear()
    monkeypatch.setenv("CRM_WORKFLOW_NOTE_LIMIT", "2")

    response = client.post(
        "/api/crm/chat/send",
        json={"message": "我要维护一下乔安禾的客户关系"},
    )
    assert response.status_code == 200
    payload = response.json()

    workflow_component = next(component for component in payload["ui_schema"] if component["component_type"] == "workflow_checkpoint")
    assert len(workflow_component["props"]["notes"]) == 2


def test_product_recommendation_snapshot_tracks_all_visible_products() -> None:
    RESPONSE_CACHE.clear()

    response = client.post(
        "/api/crm/chat/send",
        json={"message": "找6件适合夏天穿的衣服"},
    )
    assert response.status_code == 200
    payload = response.json()

    product_component = next(component for component in payload["ui_schema"] if component["component_type"] == "product_grid")
    visible_ids = [item["id"] for item in product_component["props"]["items"]]

    assert len(visible_ids) == 6
    assert payload["meta"]["focus_scope"]["product_ids"] == visible_ids
    assert payload["meta"]["session_snapshot"]["last_entity_ids"] == visible_ids


def test_customer_memory_brief_limit_respects_config(monkeypatch) -> None:
    monkeypatch.setenv("CRM_MEMORY_BRIEF_LIMIT", "2")

    response = client.get("/api/crm/customers/C285")
    assert response.status_code == 200
    payload = response.json()

    memory_component = next(component for component in payload["ui_schema"] if component["component_type"] == "memory_briefs")
    assert len(memory_component["props"]["items"]) == 2


def test_product_display_tag_limit_respects_config(monkeypatch) -> None:
    RESPONSE_CACHE.clear()
    monkeypatch.setenv("CRM_PRODUCT_TAG_LIMIT", "2")

    response = client.post(
        "/api/crm/chat/send",
        json={"message": "找5件适合夏天穿的衣服"},
    )
    assert response.status_code == 200
    payload = response.json()

    product_component = next(component for component in payload["ui_schema"] if component["component_type"] == "product_grid")
    assert product_component["props"]["items"]
    assert all(len(item["display_tags"]) <= 2 for item in product_component["props"]["items"])


def test_rejection_flow() -> None:
    response = client.post("/api/crm/chat/send", json={"message": "说说优衣库和政治新闻"})
    assert response.status_code == 200
    data = response.json()
    assert data["safety_status"] == "rejected"
    assert data["ui_schema"][0]["component_type"] == "safety_notice"


def test_detail_and_task_completion() -> None:
    with get_connection() as connection:
        connection.execute("UPDATE follow_up_tasks SET status = 'open' WHERE id = 'T001'")
        connection.commit()

    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "把今天到期还没完成的回访任务按优先级排一下"},
    )
    assert chat_response.status_code == 200
    task_component = next(
        component for component in chat_response.json()["ui_schema"] if component["component_type"] == "task_list"
    )
    task_id = task_component["props"]["items"][0]["id"]

    task_response = client.post(f"/api/crm/tasks/{task_id}/complete", headers=AUTH_HEADERS)
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "done"

    customer_response = client.get("/api/crm/customers/C001")
    assert customer_response.status_code == 200
    assert customer_response.json()["entity_type"] == "customer"
    assert "memory_briefs" in [component["component_type"] for component in customer_response.json()["ui_schema"]]
    assert "memory_suggestions" in [component["component_type"] for component in customer_response.json()["ui_schema"]]

    product_response = client.get("/api/crm/products/P001")
    assert product_response.status_code == 200
    assert product_response.json()["entity_type"] == "product"


def test_task_completion_invalidates_cached_task_query() -> None:
    RESPONSE_CACHE.clear()
    with get_connection() as connection:
        connection.execute("UPDATE follow_up_tasks SET status = 'open' WHERE id = 'T001'")
        connection.commit()

    first = client.post(
        "/api/crm/chat/send",
        json={"message": "把今天到期还没完成的回访任务按优先级排一下"},
    )
    assert first.status_code == 200
    first_payload = first.json()
    session_id = first_payload["session_id"]
    first_task_component = next(
        component for component in first_payload["ui_schema"] if component["component_type"] == "task_list"
    )
    first_task_ids = [item["id"] for item in first_task_component["props"]["items"]]
    assert "T001" in first_task_ids

    complete = client.post("/api/crm/tasks/T001/complete", headers=AUTH_HEADERS)
    assert complete.status_code == 200

    second = client.post(
        "/api/crm/chat/send",
        json={
            "session_id": session_id,
            "message": "把今天到期还没完成的回访任务按优先级排一下",
        },
    )
    assert second.status_code == 200
    second_payload = second.json()
    second_task_component = next(
        component for component in second_payload["ui_schema"] if component["component_type"] == "task_list"
    )
    second_task_ids = [item["id"] for item in second_task_component["props"]["items"]]

    assert "T001" not in second_task_ids
    assert second_payload["meta"]["repeat_query_mode"] in {"fresh", "preserve"}


def test_session_detail_and_memory_suggestion_promotion_flow() -> None:
    RESPONSE_CACHE.clear()
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM customer_memory_suggestions
            WHERE customer_id IN (SELECT id FROM customers WHERE name = '乔安禾')
            """
        )
        connection.execute(
            """
            DELETE FROM customer_memory_notes
            WHERE source = 'approved-suggestion'
              AND customer_id IN (SELECT id FROM customers WHERE name = '乔安禾')
            """
        )
        connection.execute(
            """
            DELETE FROM customer_memory_facts
            WHERE customer_id IN (SELECT id FROM customers WHERE name = '乔安禾')
              AND source_type IN ('advisor-observation', 'advisor-chat', 'advisor-chat-conflict', 'approved-suggestion')
            """
        )
        connection.commit()

    first = client.post(
        "/api/crm/chat/send",
        json={"message": "我要维护一下乔安禾的客户关系"},
    )
    session_id = first.json()["session_id"]

    observation = client.post(
        "/api/crm/chat/send",
        json={
            "session_id": session_id,
            "message": "乔安禾最近好像更偏轻薄外套，通勤时不太想穿半裙",
        },
    )
    assert observation.status_code == 200
    observation_payload = observation.json()
    assert "memory_suggestions" in [component["component_type"] for component in observation_payload["ui_schema"]]

    customer_id = observation_payload["ui_schema"][0]["props"]["item"]["id"]
    customer_detail = client.get(f"/api/crm/customers/{customer_id}")
    assert customer_detail.status_code == 200
    suggestion_component = next(
        component for component in customer_detail.json()["ui_schema"] if component["component_type"] == "memory_suggestions"
    )
    suggestion_id = suggestion_component["props"]["items"][0]["id"]

    approve = client.post(f"/api/crm/memory-suggestions/{suggestion_id}/approve", headers=AUTH_HEADERS)
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    refreshed_customer = client.get(f"/api/crm/customers/{customer_id}")
    memory_component = next(
        component for component in refreshed_customer.json()["ui_schema"] if component["component_type"] == "memory_briefs"
    )
    assert any("轻薄外套" in item["content"] for item in memory_component["props"]["items"])

    session_detail = client.get(f"/api/crm/sessions/{session_id}")
    assert session_detail.status_code == 200
    assert session_detail.json()["entity_type"] == "session"
    checkpoint_component = next(
        component for component in session_detail.json()["ui_schema"] if component["component_type"] == "session_checkpoint_list"
    )
    assert len(checkpoint_component["props"]["items"]) >= 2


def test_mutation_endpoints_require_identity_headers() -> None:
    task_response = client.post("/api/crm/tasks/T001/complete")
    assert task_response.status_code == 401

    approve_response = client.post("/api/crm/memory-suggestions/1/approve")
    assert approve_response.status_code == 401


def test_approved_memory_update_changes_follow_up_product_ranking() -> None:
    RESPONSE_CACHE.clear()
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM customer_memory_notes
            WHERE source = 'advisor-chat'
              AND customer_id IN (SELECT id FROM customers WHERE name = '乔安禾')
            """
        )
        connection.execute(
            """
            DELETE FROM customer_memory_facts
            WHERE customer_id IN (SELECT id FROM customers WHERE name = '乔安禾')
              AND source_type IN ('advisor-observation', 'advisor-chat', 'advisor-chat-conflict', 'approved-suggestion')
            """
        )
        connection.commit()

    first = client.post(
        "/api/crm/chat/send",
        json={"message": "我要维护一下乔安禾的客户关系"},
    )
    assert first.status_code == 200
    first_payload = first.json()
    session_id = first_payload["session_id"]
    spotlight = first_payload["ui_schema"][0]["props"]["item"]
    assert spotlight["name"] == "乔安禾"

    memory_update = client.post(
        "/api/crm/chat/send",
        json={
            "session_id": session_id,
            "message": "乔安禾最近好像更偏轻薄外套，通勤时不太想穿半裙",
        },
    )
    assert memory_update.status_code == 200
    memory_payload = memory_update.json()
    assert memory_payload["safety_status"] == "allowed"
    assert "memory_suggestions" in [component["component_type"] for component in memory_payload["ui_schema"]]

    customer_detail = client.get(f"/api/crm/customers/{spotlight['id']}")
    assert customer_detail.status_code == 200
    suggestion_component = next(
        component for component in customer_detail.json()["ui_schema"] if component["component_type"] == "memory_suggestions"
    )
    suggestion_id = suggestion_component["props"]["items"][0]["id"]
    approve = client.post(f"/api/crm/memory-suggestions/{suggestion_id}/approve", headers=AUTH_HEADERS)
    assert approve.status_code == 200

    with get_connection() as connection:
        stored_note = connection.execute(
            """
            SELECT content
            FROM customer_memory_notes
            WHERE customer_id = ? AND source = 'approved-suggestion'
            ORDER BY id DESC
            LIMIT 1
            """,
            (spotlight["id"],),
        ).fetchone()
    assert stored_note is not None
    assert stored_note["content"] == "最近好像更偏轻薄外套，通勤时不太想穿半裙"

    follow_up = client.post(
        "/api/crm/chat/send",
        json={
            "session_id": session_id,
            "message": "按她的喜好推荐几件产品",
        },
    )
    assert follow_up.status_code == 200
    follow_up_payload = follow_up.json()
    product_component = next(
        component for component in follow_up_payload["ui_schema"] if component["component_type"] == "product_grid"
    )
    items = product_component["props"]["items"]
    assert items[0]["category"] == "外套"
    assert sum(1 for item in items if item["category"] == "外套") >= 2
    assert all(item["category"] != "半裙" for item in items)
