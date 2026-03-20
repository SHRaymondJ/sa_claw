# CRM Agent 分支与发布规范

## 固定分支

- `main`
- `develop`
- `test`

## 功能分支

命名格式：

`codex/v{版本号}-{任务短名}`

示例：

- `codex/v1.0-stability-contract`
- `codex/v1.1-semantic-evals`

## 日常流转

1. 从 `develop` 切功能分支
2. 小任务开发和测试完成
3. 合回 `develop`
4. 大版本完成后 `develop -> test`
5. `test` 环境全量回归
6. `test -> main`
7. `main` 环境回归

## 合并要求

- 不允许跳过 `test` 直接合入 `main`
- 不允许未通过回归就打版本
- 所有合并前必须确认文档同步更新

## 版本标签

- `v0.1.0`
- `v1.0.0`
- `v1.1.0`
- `v1.2.0`
- `v1.3.0`
- `v1.4.0`

## 上线后回归

`main` 合并完成后必须检查：

- `/health`
- `/crm`
- 关键聊天链路
- 关键详情链路
- 任务动作链路
- 拒答边界
