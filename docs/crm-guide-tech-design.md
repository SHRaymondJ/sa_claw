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

### 3.4 编排策略

- 工具优先
- 生成只用于任务摘要、话术润色和说明文本
- 实体详情、库存、任务状态都以数据库查询结果为准

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

## 7. Pencil 设计前置说明

按计划，正式编码前应先完成 Pencil 设计稿；但当前 MCP 无法连接运行中的 Pencil 桌面应用，错误为：

`failed to connect to running Pencil app: visual_studio_code`

因此一期先以设计规格文档和前端实现对齐推进，并将该连接修复作为显式阻塞任务保留。
