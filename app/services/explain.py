from app.schemas import ExplainResponse, ExplainSection


def get_explain_payload() -> ExplainResponse:
    return ExplainResponse(
        title="工作台设计说明",
        subtitle="把协议、渲染、动作、数据库与维护流程放到同一张说明图里，便于汇报和学习。",
        sections=[
            ExplainSection(
                key="a2ui",
                title="协议层与渲染层",
                summary="后端只返回标准化协议，前端再用 registry 做本地实现映射。",
                points=[
                    "服务端只返回标准化组件和动作，不直接决定前端具体实现。",
                    "前端用 renderer registry 把 component_type 映射到本地组件。",
                    "前端用 action registry 把 action_type 映射到详情查询、任务完成等动作。",
                ],
                steps=[
                    "后端输出 component_type 和 action_type",
                    "前端先校验白名单",
                    "命中 registry 后再渲染或执行",
                    "未知协议统一降级，不越权执行",
                ],
                tags=["A2UI", "renderer registry", "action registry", "schema version"],
            ),
            ExplainSection(
                key="data",
                title="数据库与真实后链路",
                summary="客户、商品、库存、任务都来自数据库，卡片点击后走真实实体接口。",
                points=[
                    "客户、商品、库存和任务都来自 SQLite，而不是 Python 里的写死数组。",
                    "每张卡片都带真实实体 ID，点击后走详情接口或动作接口。",
                    "一期不用向量检索，结构化场景先用关系型数据库做稳定闭环。",
                ],
                steps=[
                    "聊天请求先过导购域意图网关",
                    "编排层查询数据库服务",
                    "返回客户卡、商品卡、任务卡和沟通建议",
                    "点击卡片后再拉取详情或执行动作",
                ],
                tags=["SQLite", "entity id", "detail api", "tool-first"],
            ),
            ExplainSection(
                key="maintenance",
                title="后续更新机制",
                summary="页面、组件和协议三层更新节奏不同，需要分别治理。",
                points=[
                    "页面更新：先改设计稿或页面规范，再改布局与 renderer，最后跑回归测试。",
                    "组件更新：先改 design token，再改基础组件，并校验 registry 映射。",
                    "协议更新：新增 schema 版本，保留兼容期，并同步更新解释页。",
                ],
                steps=[
                    "先改规格文档或设计稿",
                    "再改 token / 基础组件 / 页面组合",
                    "最后跑单测、构建和 E2E",
                ],
                tags=["design token", "visual regression", "compatibility"],
            ),
            ExplainSection(
                key="cost",
                title="成本与边界保护",
                summary="优先查库，再做生成，避免把每轮对话都变成高成本长上下文调用。",
                points=[
                    "同会话重复请求优先走缓存，减少重复生成。",
                    "生成层只消费必要字段，不把整批实体数据直接塞进上下文。",
                    "越界问题在网关层拒绝，不进入下游查询和生成。",
                ],
                steps=[
                    "摘要压缩最近回合",
                    "复用 session_id 与缓存键",
                    "字段白名单裁剪后再交给文案生成",
                ],
                tags=["cache", "summary", "guardrail", "tool-first"],
            ),
        ],
        maintenance_checklist=[
            "页面结构改动前先更新页面规范或 Pencil 稿",
            "组件样式改动前先改 design token，再改基础组件",
            "协议字段变更时增加 schema version 并保留兼容期",
            "每次发布前跑 pytest、vitest、vite build、playwright",
        ],
        blockers=[
            "Pencil 正式导出图已补齐，但原始 .pen 文件还没有固定保存到仓库路径。",
            "托管远端仓库尚未创建；当前机器具备 GitHub SSH 访问能力，但没有可直接写仓的 API 登录态。",
        ],
        protocol_example={
            "session_id": "s_xxx",
            "messages": ["user", "assistant"],
            "ui_schema": [
                {"component_type": "customer_list", "action_type": "open_customer"},
                {"component_type": "task_list", "action_type": "complete_task"},
            ],
            "safety_status": "allowed",
            "context_version": "crm-v1",
        },
    )
