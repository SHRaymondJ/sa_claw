from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.config import get_app_settings
from app.schemas import ActionMutationResponse, BootstrapResponse, CRMChatRequest, CRMChatResponse, EntityDetailResponse, ExplainResponse, TaskCompleteResponse
from app.services.access_control import build_request_actor, enforce_rate_limit
from app.services.crm_service import (
    approve_memory_suggestion,
    complete_task,
    get_bootstrap_payload,
    get_customer_detail,
    get_product_detail,
    get_session_detail,
    get_task_detail,
    reject_memory_suggestion,
    send_chat,
)
from app.services.explain import get_explain_payload


router = APIRouter(prefix="/api/crm", tags=["crm"])


@router.get("/bootstrap", response_model=BootstrapResponse)
def bootstrap() -> BootstrapResponse:
    return BootstrapResponse(**get_bootstrap_payload())


@router.post("/chat/send", response_model=CRMChatResponse)
def chat_send(
    payload: CRMChatRequest,
    x_advisor_id: Optional[str] = Header(default=None),
    x_store_id: Optional[str] = Header(default=None),
) -> CRMChatResponse:
    settings = get_app_settings()
    actor = build_request_actor(
        settings,
        advisor_id=x_advisor_id,
        store_id=x_store_id,
        require_identity=False,
    )
    session_token = payload.session_id or "new-session"
    enforce_rate_limit(
        "chat",
        f"{actor.advisor_id}:{session_token}",
        limit=settings.chat_rate_limit,
        window_seconds=settings.chat_rate_window_seconds,
    )
    return send_chat(payload.message, payload.session_id, actor=actor)


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


@router.get("/sessions/{session_id}", response_model=EntityDetailResponse)
def session_detail(session_id: str) -> EntityDetailResponse:
    try:
        return get_session_detail(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


@router.post("/tasks/{task_id}/complete", response_model=TaskCompleteResponse)
def task_complete(
    task_id: str,
    x_advisor_id: Optional[str] = Header(default=None),
    x_store_id: Optional[str] = Header(default=None),
) -> TaskCompleteResponse:
    settings = get_app_settings()
    actor = build_request_actor(
        settings,
        advisor_id=x_advisor_id,
        store_id=x_store_id,
        require_identity=True,
    )
    enforce_rate_limit(
        "mutation",
        actor.advisor_id,
        limit=settings.mutation_rate_limit,
        window_seconds=settings.mutation_rate_window_seconds,
    )
    try:
        return complete_task(task_id, actor=actor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc


@router.get("/tasks/{task_id}", response_model=EntityDetailResponse)
def task_detail(task_id: str) -> EntityDetailResponse:
    try:
        return get_task_detail(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc


@router.post("/memory-suggestions/{suggestion_id}/approve", response_model=ActionMutationResponse)
def memory_suggestion_approve(
    suggestion_id: int,
    x_advisor_id: Optional[str] = Header(default=None),
    x_store_id: Optional[str] = Header(default=None),
) -> ActionMutationResponse:
    settings = get_app_settings()
    actor = build_request_actor(
        settings,
        advisor_id=x_advisor_id,
        store_id=x_store_id,
        require_identity=True,
    )
    enforce_rate_limit(
        "mutation",
        actor.advisor_id,
        limit=settings.mutation_rate_limit,
        window_seconds=settings.mutation_rate_window_seconds,
    )
    try:
        return approve_memory_suggestion(suggestion_id, actor=actor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="memory suggestion not found") from exc


@router.post("/memory-suggestions/{suggestion_id}/reject", response_model=ActionMutationResponse)
def memory_suggestion_reject(
    suggestion_id: int,
    x_advisor_id: Optional[str] = Header(default=None),
    x_store_id: Optional[str] = Header(default=None),
) -> ActionMutationResponse:
    settings = get_app_settings()
    actor = build_request_actor(
        settings,
        advisor_id=x_advisor_id,
        store_id=x_store_id,
        require_identity=True,
    )
    enforce_rate_limit(
        "mutation",
        actor.advisor_id,
        limit=settings.mutation_rate_limit,
        window_seconds=settings.mutation_rate_window_seconds,
    )
    try:
        return reject_memory_suggestion(suggestion_id, actor=actor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="memory suggestion not found") from exc


@router.get("/explain", response_model=ExplainResponse)
def explain() -> ExplainResponse:
    return get_explain_payload()
