from app.schemas import ExplainResponse, ExplainSection


def get_explain_payload() -> ExplainResponse:
    return ExplainResponse(
        title="工作台设计说明",
        sections=[
            ExplainSection(
                key="a2ui",
                title="协议层与渲染层",
                points=[
                    "服务端只返回标准化组件和动作，不直接决定前端具体实现。",
                    "前端用 renderer registry 把 component_type 映射到本地组件。",
                    "前端用 action registry 把 action_type 映射到详情查询、任务完成等动作。",
                ],
            ),
            ExplainSection(
                key="data",
                title="数据库与真实后链路",
                points=[
                    "客户、商品、库存和任务都来自 SQLite，而不是 Python 里的写死数组。",
                    "每张卡片都带真实实体 ID，点击后走详情接口或动作接口。",
                    "一期不用向量检索，结构化场景先用关系型数据库做稳定闭环。",
                ],
            ),
            ExplainSection(
                key="maintenance",
                title="后续更新机制",
                points=[
                    "页面更新：先改设计稿或页面规范，再改布局与 renderer，最后跑回归测试。",
                    "组件更新：先改 design token，再改基础组件，并校验 registry 映射。",
                    "协议更新：新增 schema 版本，保留兼容期，并同步更新解释页。",
                ],
            ),
        ],
    )
