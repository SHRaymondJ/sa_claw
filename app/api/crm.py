from fastapi import APIRouter, HTTPException

from app.schemas import BootstrapResponse, CRMChatRequest, CRMChatResponse, EntityDetailResponse, ExplainResponse, TaskCompleteResponse
from app.services.crm_service import complete_task, get_bootstrap_payload, get_customer_detail, get_product_detail, get_task_detail, send_chat
from app.services.explain import get_explain_payload


router = APIRouter(prefix="/api/crm", tags=["crm"])


@router.get("/bootstrap", response_model=BootstrapResponse)
def bootstrap() -> BootstrapResponse:
    return BootstrapResponse(**get_bootstrap_payload())


@router.post("/chat/send", response_model=CRMChatResponse)
def chat_send(payload: CRMChatRequest) -> CRMChatResponse:
    return send_chat(payload.message, payload.session_id)


@router.get("/customers/{customer_id}", response_model=EntityDetailResponse)
def customer_detail(customer_id: str) -> EntityDetailResponse:
    try:
        return get_customer_detail(customer_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="customer not found") from exc


@router.get("/products/{product_id}", response_model=EntityDetailResponse)
def product_detail(product_id: str) -> EntityDetailResponse:
    try:
        return get_product_detail(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="product not found") from exc


@router.post("/tasks/{task_id}/complete", response_model=TaskCompleteResponse)
def task_complete(task_id: str) -> TaskCompleteResponse:
    try:
        return complete_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc


@router.get("/tasks/{task_id}", response_model=EntityDetailResponse)
def task_detail(task_id: str) -> EntityDetailResponse:
    try:
        return get_task_detail(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc


@router.get("/explain", response_model=ExplainResponse)
def explain() -> ExplainResponse:
    return get_explain_payload()
