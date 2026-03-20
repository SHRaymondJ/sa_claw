# 服装品牌导购工作台技术设计

## 1. 总体架构

```text
React 工作台
  -> 协议 renderer / action registry
  -> FastAPI API 层
  -> 导购域意图网关
  -> 编排服务
  -> 数据服务 / SQLite
  -> 生成适配层
```

## 2. 前端设计

### 2.1 技术选型

- React + Vite：前端工程和快速构建
- Tailwind：design token 和页面样式约束
- shadcn/ui：实现层基础组件
- A2UI：协议层，不绑定具体组件库

### 2.2 为什么 `shadcn/ui` 适合作为实现层

- 更适合 React 下快速搭抽屉、卡片、按钮和表单
- 基础组件结构清晰，便于写测试
- 代码在本地仓库中可控，不依赖黑盒运行时
- 可以通过 design token 统一收口视觉风格

### 2.3 A2UI 与组件库的边界

- A2UI 定义返回的 `component_type`、`action_type`、数据结构和兼容规则
- `renderer registry` 负责把协议组件映射到 React 组件
- `action registry` 负责把协议动作映射到前端行为和 API 请求
- `shadcn/ui` 只负责提供组件壳层，不参与协议定义

## 3. 后端设计

### 3.1 API

- `GET /crm`
- `POST /api/crm/chat/send`
- `GET /api/crm/customers/{id}`
- `GET /api/crm/products/{id}`
- `POST /api/crm/tasks/{id}/complete`
- `GET /api/crm/explain`
- `GET /health`

### 3.2 会话协议

响应字段固定为：

- `session_id`
- `messages[]`
- `ui_schema[]`
- `supported_actions[]`
- `safety_status`
- `context_version`

### 3.3 意图网关

第一层先做规则判断：

- 只放行客户筛选、商品推荐、库存查询、任务处理、话术整理、跟进建议
- 命中其他品牌、政治、泛商业评论时直接返回拒答卡片
- 不进入数据库查询和生成链路
- 当模型输出与显式导购域规则冲突时，优先采用规则与会话上下文，不让正常导购问题被错拒

### 3.4 编排策略

- 工具优先
- 生成只用于任务摘要、话术润色和说明文本
- 实体详情、库存、任务状态都以数据库查询结果为准
- 聊天主链路固定拆成：硬边界判定 -> 问题类型判断 -> 上下文解析 -> 结果编排

### 3.5 内部决策契约

- `question_type`：内部问题类型，决定应该走哪类结果编排
- `response_shape`：内部响应形态字符串，用于会话状态、回归测试和 explain 页面
- `repeat_query_mode`：重复提问处理模式，当前取值为 `fresh / preserve / diversify`
- `stability_mode`：当前结果的稳定性口径，区分实体稳定、换批刷新和文本可变
- `conversation_mode`：当前对话所处工作模式，例如客户洞察、商品推荐、客户维护、话术整理
- `handoff_reason`：为什么从上一轮模式切换到当前模式，供前端状态条和会话详情展示
- `working_memory_summary`：当前工作记忆摘要，帮助缓存、解释页与长对话稳定回看
- `context_resolution`：当前回合的上下文解析结果，至少包含：
  - `active_customer_id`
  - `active_customer_name`
  - `reused_from_session`
  - `resolution_confidence`
- `session_snapshot`：会话状态最小快照，至少包含：
  - `active_customer_id`
  - `active_customer_name`
  - `active_intent`
  - `conversation_mode`
  - `last_response_shape`
  - `last_entity_ids`
  - `handoff_reason`
  - `working_memory_summary`
- `visible_entity_contract`：凡是当前轮真实展示给用户的商品、任务实体，都必须与：
  - `focus_scope.product_ids / task_ids`
  - `session_snapshot.last_entity_ids`
  - 响应 meta 中的最终实体集合
  保持一致，禁止前端展示 6 条而状态层只记前 4 条的隐式截断

### 3.6 多轮状态机

- 对话主链路不再只是一次性 `question_type -> response_shape`，而是显式维护多轮状态机
- 状态机最少包含：
  - `conversation_mode`
  - `focus_scope`
  - `handoff_reason`
  - `working_memory_summary`
- 重复提问策略固定为：
  - 同会话重复同一问题，默认 `preserve`
  - 出现 `换一批 / 再来几件 / 看看别的` 等不满意信号时进入 `diversify`
  - `diversify` 会沿用上一轮条件，但主动避开上一批实体结果
- 继承规则采用“保守继承 + 明确切换”：
  - 代词追问只在上一轮明确锁定客户时继承
  - 用户命名新客户时立刻切换焦点
  - 用户从客户问题切到任务问题时默认清空客户焦点
- 缓存键必须带上会话模式和工作记忆摘要，避免不同阶段误命中旧响应
- 同一轮如果前端可见实体数量发生变化，会话状态、缓存写入和响应 meta 必须同步使用“当前可见实体集合”，不能各自再做二次切片

### 3.7 响应形态约束表

| 问题类型 | 固定响应形态 |
| --- | --- |
| 客户总览 | `customer_overview + workflow_checkpoint + customer_list` |
| 客户筛选 | `workflow_checkpoint + customer_list` |
| 客户洞察 | `customer_spotlight + detail_kv + tag_group + memory_briefs` |
| 商品推荐 | `product_grid` |
| 指定客户商品推荐 | `customer_spotlight + workflow_checkpoint + product_grid` |
| 客户维护 | `customer_spotlight + workflow_checkpoint + relationship_plan + knowledge_briefs + product_grid` |
| 沟通话术 | `customer_spotlight + workflow_checkpoint + [可选 product_grid] + message_draft` |
| 品类盘点 | `category_overview` |
| 客户标签总览 | `tag_group` |
| 任务处理 | `task_list` 或 `workflow_checkpoint + task_list` |
| 越界拒答 | `safety_notice` |

### 3.9 去写死配置基线

- 默认返回数量、客户总览样本数、维护场景商品数和快捷提示不再由服务代码直接写死
- 上述策略统一由配置层提供，支持通过环境变量覆盖
- 当前已完成第一批迁移：
  - `CRM_DEFAULT_RESULT_COUNT`
  - `CRM_MAX_RESULT_COUNT`
  - `CRM_CUSTOMER_SAMPLE_LIMIT`
  - `CRM_RELATIONSHIP_PRODUCT_LIMIT`
  - `CRM_QUICK_PROMPTS`
- 当前已完成第二批清理：
  - 商品推荐和任务结果的内部状态不再固定截断为 `4`
  - 前端测试与 E2E 已移除把 demo 数字当作协议契约的断言
- 当前已完成第三批迁移：
  - `CRM_WORKFLOW_NOTE_LIMIT`
  - `CRM_MEMORY_BRIEF_LIMIT`
- 当前已完成第四批迁移：
  - `CRM_PRODUCT_TAG_LIMIT`
  - `GuardrailResult.requested_count` 默认值已改为读取配置层
- 当前已完成第五批清理：
  - 前端头部不再回退到 demo 品牌、门店和导购姓名
  - bootstrap 字段缺失时改为展示中性占位，避免 UI 伪造业务身份

### 3.8 分层记忆治理

- 记忆拆成 3 层：
  - 工作记忆：本轮目标、当前客户、最近动作结果
  - 会话记忆：本会话已确认偏好、当前阶段、最近观察
  - 长期记忆：已确认的稳定偏好、服务提示、禁忌项
- 晋升规则：
  - 只有导购显式备注、用户明确要求记住、或重复稳定出现时才允许进入长期记忆
  - 会话结束后，会话记忆不会自动晋升为长期记忆
- 冲突规则：
  - 新观察若与已确认长期记忆冲突，只能进入待确认，不可直接覆盖
  - 来源优先级固定为：导购显式确认 > 待确认观察 > 历史弱提示

## 4. 数据设计

### 4.1 一期为何不用向量存储

- 一期核心是结构化导购工作流，不是知识问答
- 客户、商品、库存、任务主要是标准化字段查询
- 当前规模下关系型数据库更简单、可控、可解释
- 先把实体后链路和协议渲染做扎实，比提前引入向量更有价值

### 4.2 二期向量存储引入边界

二期只为以下非结构化内容提供补充召回：

- 商品卖点说明
- 导购 SOP
- 历史沟通摘要
- 训练好的话术库
- 门店知识和活动说明

结构化实体检索仍保留在关系型数据库中，不交给向量检索替代。

### 4.3 一期数据表

- `customers`
- `customer_tags`
- `products`
- `inventory`
- `follow_up_tasks`
- `interaction_logs`
- `conversation_sessions`
- `conversation_turns`

### 4.4 一期图片素材策略

- 当前首版采用本地可替换公开占位图，保证演示闭环和稳定构建
- 每个商品都保留 `image_source_name`、`image_source_url` 和 `replacement_strategy`
- 后续替换真实演示素材时，优先保持：
  - 相同宽高比
  - 相同命名规范
  - 同步更新来源字段
  - 替换后重新跑构建与 E2E

## 5. token 与成本保护

- 摘要缓存：只保留最近少量回合摘要
- 重复请求缓存：同会话重复问题优先命中缓存
- 实体 ID 化：对生成层传递精简字段而不是整表
- 字段白名单裁剪：仅传递必要字段
- 长度限制：单轮输入与历史上下文设上限
- 工具优先：能查数据库就不走生成

## 6. 页面、组件、协议更新机制

### 6.1 页面级更新

1. 先更新 Pencil 稿或页面设计说明
2. 更新页面规范文档
3. 调整 layout 和 renderer 组合
4. 跑视觉回归、交互回归和 E2E

### 6.2 组件样式更新

1. 先修改 design token
2. 再修改基础组件
3. 验证 registry 映射未被破坏
4. 跑单测、视觉回归和 E2E

### 6.3 协议级更新

1. 增加 schema 版本
2. 保留兼容期
3. 更新 explain 页面
4. 给未知协议提供降级渲染

### 6.4 聊天稳定化回归

1. 先跑后端集成测试，确认 `safety_status`、`question_type` 对应形态和摘要口径
2. 再跑前端组件测试，确认关键协议组件仍可稳定渲染
3. 再跑 E2E，覆盖移动端和桌面端的高频追问链路
4. 最后按真人乱问清单逐条试问，确认不会出现错拒、错路由、错继承、错组件返回

### 6.5 长对话回归要求

1. 同一客户连续 5 轮追问，不得跳回客户清单或丢失客户焦点
2. A 客户切到 B 客户后，代词追问只能落到最近明确锁定客户
3. 客户维护 -> 商品推荐 -> 话术整理三段链路必须稳定迁移
4. 客户问题 -> 任务问题 -> 再回客户问题时，客户焦点只在明确重新锁定后恢复
5. 待确认观察被导购确认后，后续推荐与话术允许引用该记忆

### 6.6 素材更新

1. 先确认素材来源可追溯、可替换
2. 替换 `products` 数据中的来源字段
3. 若换成本地图，保持原路径规则或同步更新 seed 数据
4. 跑页面检查、构建和 E2E，确认没有图片断链

## 7. Pencil 设计交付说明

Pencil 桌面连接已经恢复，本轮已补齐以下正式设计导出图：

- 移动端主工作台
- 移动端详情抽屉
- 移动端拒答态
- PC 端工作台
- 说明页

导出物位于：

- `designs/pencil-exports/GoEJp.png`
- `designs/pencil-exports/lJZOy.png`
- `designs/pencil-exports/LAoMv.png`
- `designs/pencil-exports/QIctY.png`
- `designs/pencil-exports/BhEkG.png`

当前仍有一个设计资产层面的已知限制：

- 可以稳定连接、编辑和导出，但 Pencil 临时文档尚未自动落到仓库内固定 `.pen` 文件路径
- 因此本次交付先以正式导出图和设计索引为准，后续如需把 `.pen` 原文件纳入版本管理，需要在桌面端明确保存路径
