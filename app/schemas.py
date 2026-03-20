from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CRMAction(BaseModel):
    action_type: str
    label: str
    entity_type: str
    entity_id: Optional[str] = None
    method: Literal["GET", "POST"] = "GET"
    variant: Literal["primary", "secondary", "ghost"] = "secondary"
    payload: dict[str, Any] = Field(default_factory=dict)


class CRMComponent(BaseModel):
    component_type: str
    component_id: str
    title: str
    props: dict[str, Any] = Field(default_factory=dict)
    actions: list[CRMAction] = Field(default_factory=list)


class CRMMessage(BaseModel):
    message_id: str
    role: Literal["user", "assistant", "system"]
    text: str
    created_at: str
    ui_schema: list[CRMComponent] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class CRMChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=320)
    session_id: Optional[str] = None


class CRMChatResponse(BaseModel):
    session_id: str
    messages: list[CRMMessage]
    ui_schema: list[CRMComponent]
    supported_actions: list[str]
    safety_status: Literal["allowed", "rejected"]
    context_version: str
    meta: dict[str, Any] = Field(default_factory=dict)
    clarification_needed: bool = False


class ActionMutationResponse(BaseModel):
    entity_id: str
    status: str
    message: str
    session_meta: dict[str, Any] = Field(default_factory=dict)
    updated_component: Optional[CRMComponent] = None


class EntityDetailResponse(BaseModel):
    entity_type: Literal["customer", "product", "task", "session"]
    entity_id: str
    title: str
    subtitle: str
    summary: str
    ui_schema: list[CRMComponent]


class TaskCompleteResponse(BaseModel):
    task_id: str
    status: str
    message: str
    updated_component: CRMComponent
    session_meta: dict[str, Any] = Field(default_factory=dict)


class ExplainSection(BaseModel):
    key: str
    title: str
    summary: str
    points: list[str]
    steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ExplainResponse(BaseModel):
    title: str
    subtitle: str
    sections: list[ExplainSection]
    maintenance_checklist: list[str]
    blockers: list[str]
    protocol_example: dict[str, Any]


class BootstrapResponse(BaseModel):
    advisor_id: str
    advisor_name: str
    store_id: str
    store_name: str
    brand_name: str
    pending_task_count: int
    quick_prompts: list[str]
