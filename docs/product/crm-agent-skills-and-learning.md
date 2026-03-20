# CRM Agent Skills 与学习治理

## 目标

把系统从“散乱规则堆叠”升级为“技能驱动 + 受治理学习”的产品能力体系。

## 产品内 Skills

首批技能：

- `customer_screening_skill`
- `product_recommendation_skill`
- `relationship_maintenance_skill`
- `message_drafting_skill`
- `inventory_lookup_skill`
- `clarification_skill`
- `safety_boundary_skill`
- `memory_capture_skill`

## 每个 Skill 必须定义

- 适用问题
- 输入契约
- 允许调用的工具
- 可输出的 schema 白名单
- 失败回退
- 安全边界

## 学习对象分离

### 客户记忆

- 面向具体客户
- 记录偏好、禁忌、服务提示
- 审批前不得进入长期事实

### 系统学习

- 面向整体产品
- 记录高价值问法、失败样本、策略修正点、schema 优化建议

### 失败样本

- 面向测试和回归
- 每个真实失败都要能补进回归集

## 学习治理

采用 `审核后入长期库`：

1. 记录候选学习项
2. 进入审核队列
3. 审核决定：
   - 批准
   - 拒绝
   - 继续观察
4. 批准后进入长期规则或长期知识

## 审核字段

- 候选内容
- 来源会话
- 来源问题
- 影响范围
- 风险等级
- 审核状态
- 审核人
- 生效时间
- 回滚记录

## 禁止事项

- 禁止未经审核自动改变品牌边界
- 禁止未经审核自动改变排序策略
- 禁止把客户临时观察直接升级为长期记忆
