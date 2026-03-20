# CRM Agent 生成式 UI 协议

## 目标

让复杂回答以单个语义完整的模块返回，而不是拆成多个松散块，同时保持安全、可测和可兼容。

## 协议原则

- 采用 `富组合白名单`
- Agent 有组合权，但没有任意布局权
- 前端只渲染白名单 `component_type`
- 未知 schema 必须安全降级

## 协议层级

### 原子组件

- `detail_kv`
- `tag_group`
- `timeline`
- `image_panel`
- `task_list`

### 复合语义组件

- `recommendation_bundle`
- `relationship_bundle`
- `insight_bundle`
- `clarification_bundle`
- `action_feedback_bundle`

## 复合组件要求

每个复合组件都必须带：

- `semantic_goal`
- `render_variant`
- `evidence`
- `items`
- `actions`
- `stability_mode`

## 稳定性约束

- 复合组件中的实体结果由事实层决定
- 生成层只能补理由、摘要和展示文本
- 不允许生成层自己新增数据库外实体

## 版本兼容

- 新协议字段要有默认值
- schema 升级必须记录版本
- 历史消息回放要可降级
- 新旧 renderer 允许兼容期共存

## 降级策略

当前端遇到未知复合组件时：

1. 先渲染安全解释卡
2. 显示组件标题和简述
3. 保留可执行动作
4. 记录 fallback 日志
