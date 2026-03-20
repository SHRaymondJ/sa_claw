from app.schemas import ExplainResponse, ExplainSection


def get_explain_payload() -> ExplainResponse:
    return ExplainResponse(
        title="工作台设计说明",
        subtitle="把协议、渲染、动作、数据库与维护流程放到同一张说明图里，便于汇报和学习。",
        sections=[
            ExplainSection(
                key="stabilization",
                title="稳定化整治思路",
                summary="本轮先把对话正确性稳住，再去提升自然感，避免系统看起来会聊天但经不起随便试问。",
                points=[
                    "聊天请求会先经过硬边界、问题类型判断、上下文解析，再进入结果编排。",
                    "同类问题绑定固定返回形态，避免一次返回客户卡、一次又跳成商品卡。",
                    "会话状态除了当前客户和当前意图，还会记录最近返回形态、最近实体、当前模式和切换原因。",
                    "真实模型只做弱结构化补充和文案润色，不作为主决策源。",
                ],
                steps=[
                    "先判定是否越界",
                    "再归类成客户总览、客户洞察、商品推荐、客户维护等标准类型",
                    "根据当前会话客户和最近形态做保守继承",
                    "最后按固定响应形态输出组件",
                ],
                tags=["stabilization", "question type", "response shape", "session snapshot"],
            ),
            ExplainSection(
                key="state-machine",
                title="长对话状态机",
                summary="二期新增显式状态机，让连续追问、切客户、切任务时都有稳定的迁移规则，不靠模型临场猜。",
                points=[
                    "每轮都会维护 conversation_mode、focus_scope、handoff_reason 和 working_memory_summary。",
                    "代词追问只有在上一轮明确锁定客户时才会继承，避免跨客户串场。",
                    "从客户问题切到任务问题时，默认清空客户焦点，让任务链路单独成立。",
                    "缓存键会带上当前模式和工作记忆摘要，避免不同阶段误命中旧答案。",
                ],
                steps=[
                    "先识别当前问题属于哪一种工作模式",
                    "再判断是否沿用上一轮锁定对象",
                    "如发生切换则写入切换原因并更新工作记忆",
                    "最后按该模式固定的响应形态返回结果",
                ],
                tags=["conversation mode", "focus scope", "handoff reason", "working memory"],
            ),
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
                    "客户详情里会单独展示已记录偏好与服务提示，把长期记忆作为独立对象管理。",
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
                key="workflow-memory",
                title="工作流与记忆对象化",
                summary="把当前执行节奏和长期记忆显式做成协议组件，避免只藏在上下文变量里。",
                points=[
                    "复杂回合会返回“本轮执行节奏”，明确当前阶段、结果规模和下一步动作。",
                    "客户详情会返回“已记录偏好与服务提示”，把长期记忆、会话记忆和待确认观察分开展示。",
                    "模糊观察先进入“待确认记录”，确认后才会转为长期记忆。",
                    "只有导购显式说“记住/补充/备注”时，才会直接提升为长期记忆。",
                    "若新观察与已确认偏好冲突，系统只会挂起待确认，不会直接覆盖历史记录。",
                ],
                steps=[
                    "先识别客户与当前工作流阶段",
                    "再召回长期记忆、会话记忆和最近互动",
                    "模糊观察先落到待确认区，确认后再写入长期记忆",
                    "检测与已确认偏好的冲突，必要时保留为待确认",
                    "最后输出可执行建议，并把显式备注直接写回长期记忆",
                ],
                tags=["workflow checkpoint", "durable memory", "session memory", "pending memory"],
            ),
            ExplainSection(
                key="checkpoint-review",
                title="会话节点与可回看",
                summary="每次有效回合都会沉淀一个会话节点，方便从工作台里直接回看当前这轮是怎么推进的。",
                points=[
                    "每个有效回合都会写入会话节点，记录目标、阶段、结果规模和下一步动作。",
                    "当前会话状态里还会保留最近返回形态与最近实体，方便定位为什么这轮会这么回。",
                    "前端可通过“本轮节点”入口打开会话详情，不必翻聊天记录去猜系统状态。",
                    "这让复杂导购流程更像工作台，而不是单纯聊天窗口。",
                ],
                steps=[
                    "用户发起目标",
                    "系统整理结果并写入会话节点",
                    "导购随时打开“本轮节点”查看推进脉络",
                ],
                tags=["session checkpoints", "replay", "workflow visibility"],
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
                    "涉及状态变更的动作前端先二次确认，避免静默执行副作用。",
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
            "每轮对话链路改动后跑真人乱问回归清单，不只看自动化",
            "真人试问一旦翻车，要把失败样本补进回归清单或自动化测试",
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
                {"component_type": "workflow_checkpoint", "action_type": "open_session"},
                {"component_type": "memory_suggestions", "action_type": "approve_memory_suggestion"},
            ],
            "safety_status": "allowed",
            "context_version": "crm-v2-memory",
            "meta": {
                "conversation_mode": "relationship_maintenance",
                "handoff_reason": "沿用上一轮已锁定客户，进入关系维护。",
                "working_memory_summary": "当前围绕乔安禾维护关系，偏好通勤与轻薄外套。",
            },
        },
    )
