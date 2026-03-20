# CRM Agent 观测与问题沉淀

## 目标

商业化 agent 系统不能只靠人工感觉好不好用，必须能看见失败发生在哪一层。

## 必须建设的日志与观测

### 1. 会话决策日志

- question_type
- conversation_mode
- handoff_reason
- repeat_query_mode
- response_shape
- skill_name

### 2. 工具与数据日志

- 查询了哪些实体
- 返回了哪些候选
- 最终用了哪些实体
- mutation 前后状态

### 3. UI schema 日志

- component_type
- composite schema type
- schema version
- fallback 是否触发

### 4. 用户结果日志

- 是否采纳推荐
- 是否打开详情
- 是否执行动作
- 是否需要澄清
- 是否触发拒答

## 质量指标

- 首答命中率
- 澄清后完成率
- 推荐采纳率
- 错拒率
- 串上下文率
- 幻觉率
- 平均响应时延
- 单会话成本

## 问题记录机制

所有问题统一记入：

- 现象
- 复现方式
- 根因分类
- 修复动作
- 是否进入回归
- 影响版本

问题分类固定为：

- 计划问题
- 执行问题
- 数据问题
- 协议问题
- 测试缺失

## 发布后复盘

每个版本发布后必须更新：

- 发布总结
- 已知问题
- 新增失败样本
- 下一版修复优先级
