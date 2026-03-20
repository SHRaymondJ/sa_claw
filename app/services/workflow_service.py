from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowResolution:
    workflow_name: str
    workflow_stage: str
    rationale: str
    next_step: str


def resolve_workflow(
    *,
    intent: str,
    message: str,
    focus_customer: dict | None,
    products: list[dict],
    tasks: list[dict],
) -> WorkflowResolution:
    if intent == "relationship_maintenance":
        if not focus_customer:
            return WorkflowResolution(
                workflow_name="relationship_maintenance",
                workflow_stage="need_customer",
                rationale="当前未锁定具体客户，无法给出稳定的维护建议。",
                next_step="先确认要维护的客户，再结合偏好和最近互动生成建议。",
            )
        if products:
            return WorkflowResolution(
                workflow_name="relationship_maintenance",
                workflow_stage="maintain_with_products",
                rationale="已识别客户并召回偏好，可用一到两件现货作为关系维护切入口。",
                next_step="先轻触达，再带出一件主推款与一个替代方向。",
            )
        return WorkflowResolution(
            workflow_name="relationship_maintenance",
            workflow_stage="maintain_only",
            rationale="已识别客户，但当前没有稳定商品结果，先用关系维护打法承接。",
            next_step="先做关怀式触达，待客户反馈后再补充商品建议。",
        )

    if intent == "product_recommendation":
        return WorkflowResolution(
            workflow_name="product_recommendation",
            workflow_stage="customer_matched_recommendation" if focus_customer else "general_recommendation",
            rationale="当前目标是筛选更匹配的现货商品并组织推荐理由。",
            next_step="优先给一件最稳主推款，再补一个替代方向帮助对比。",
        )

    if intent == "customer_filter":
        return WorkflowResolution(
            workflow_name="customer_filter",
            workflow_stage="candidate_screening",
            rationale="当前目标是筛选应优先跟进的客户。",
            next_step="先锁定高优客户，再进入维护或推荐动作。",
        )

    if intent == "task_management":
        return WorkflowResolution(
            workflow_name="task_management",
            workflow_stage="task_execution",
            rationale="当前目标是处理待办任务。",
            next_step="先完成高优任务，再回到客户维护或商品推荐。",
        )

    if intent == "message_draft":
        return WorkflowResolution(
            workflow_name="message_draft",
            workflow_stage="compose_message",
            rationale="当前目标是生成可直接使用的沟通话术。",
            next_step="围绕已知客户偏好和现货结果，输出自然可发的短消息。",
        )

    if intent == "inventory_lookup":
        return WorkflowResolution(
            workflow_name="inventory_lookup",
            workflow_stage="inventory_check",
            rationale="当前目标是确认门店与仓库库存。",
            next_step="先查库存，再决定是否值得对客户发起推荐。",
        )

    return WorkflowResolution(
        workflow_name="general",
        workflow_stage="general",
        rationale="当前为通用导购对话。",
        next_step="优先收口到客户、商品、库存、任务之一的明确动作。",
    )
