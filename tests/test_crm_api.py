import os

from fastapi.testclient import TestClient

from app.main import app


os.environ["MODEL_PROVIDER"] = "mock"
os.environ["MODEL_API_KEY"] = ""

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bootstrap_and_chat_flow() -> None:
    bootstrap_response = client.get("/api/crm/bootstrap")
    assert bootstrap_response.status_code == 200
    payload = bootstrap_response.json()
    assert payload["advisor_name"]
    assert payload["pending_task_count"] > 0

    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "帮我找今天该优先跟进但还没联系的高净值客户"},
    )
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert data["safety_status"] == "allowed"
    component_types = [component["component_type"] for component in data["ui_schema"]]
    assert "customer_list" in component_types
    assert "message_draft" in component_types


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
    trace_component = next(component for component in data["ui_schema"] if component["component_type"] == "trace_timeline")
    assert "季节 夏天" in trace_component["props"]["items"][0]["detail"]


def test_rejection_flow() -> None:
    response = client.post("/api/crm/chat/send", json={"message": "说说优衣库和政治新闻"})
    assert response.status_code == 200
    data = response.json()
    assert data["safety_status"] == "rejected"
    assert data["ui_schema"][0]["component_type"] == "safety_notice"


def test_detail_and_task_completion() -> None:
    chat_response = client.post(
        "/api/crm/chat/send",
        json={"message": "把今天到期还没完成的回访任务按优先级排一下"},
    )
    assert chat_response.status_code == 200
    task_component = next(
        component for component in chat_response.json()["ui_schema"] if component["component_type"] == "task_list"
    )
    task_id = task_component["props"]["items"][0]["id"]

    task_response = client.post(f"/api/crm/tasks/{task_id}/complete")
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "done"

    customer_response = client.get("/api/crm/customers/C001")
    assert customer_response.status_code == 200
    assert customer_response.json()["entity_type"] == "customer"

    product_response = client.get("/api/crm/products/P001")
    assert product_response.status_code == 200
    assert product_response.json()["entity_type"] == "product"
