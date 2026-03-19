# 服装品牌导购工作台

这是一个移动端优先、兼容 PC 的服装品牌导购工作台产品仓库。

仓库目标不是做课堂练习，而是落地一个更接近真实零售场景的产品原型：

- 主界面是聊天式导购工作台
- 返回结果遵循协议化 UI 渲染思路
- 客户、商品、任务都带真实后链路
- 数据来自本地数据库，不靠 Python 文件里的硬编码业务结果
- 问答被严格限制在导购域和已实现的接口能力内

## 当前范围

一期范围：

- `React + Vite + Tailwind + shadcn/ui` 前端工作台
- `FastAPI` 后端 API 与静态资源托管
- `SQLite` 数据层与中等演示级种子数据
- 协议化 UI 渲染、动作分发、详情抽屉、任务闭环
- 受限问答、拒答卡片、上下文裁剪与缓存
- 单测、集成测、E2E

二期规划：

- 向量检索
- 非结构化知识召回
- 更完整的权限和门店隔离

## 目录

```text
ai-transition-lab/
  AGENTS.md
  README.md
  requirements.txt
  docs/
    crm-guide-prd.md
    crm-guide-tech-design.md
    crm-guide-task-board.md
  app/
    ...
  frontend/
    ...
  tests/
    ...
```

## 教学内容迁移

教学资料已经迁出当前产品仓库，移到：

`/Users/raymondj/Documents/Raymond/ai-transition-teaching-archive`

当前仓库只保留产品实现、设计文档、测试和脱敏配置模板。

## 开发原则

- 先规格，再实现
- 协议层与组件库解耦
- 工具优先于生成
- 真实实体 ID 驱动后链路
- 敏感信息不入仓库

## 关键文档

- [PRD](/Users/raymondj/Documents/Raymond/ai-transition-lab/docs/crm-guide-prd.md)
- [技术设计](/Users/raymondj/Documents/Raymond/ai-transition-lab/docs/crm-guide-tech-design.md)
- [任务板](/Users/raymondj/Documents/Raymond/ai-transition-lab/docs/crm-guide-task-board.md)

## 本地运行

后续以前端构建产物由 FastAPI 托管为主。

典型开发流程：

```bash
cd /Users/raymondj/Documents/Raymond/ai-transition-lab
./.venv/bin/pip install -r requirements.txt
cd frontend && pnpm install
pnpm build
cd ..
./.venv/bin/python -m uvicorn app.main:app --reload --port 8013
```

## 设计交付

- 正式 Pencil 导出图见 [designs/README.md](/Users/raymondj/Documents/Raymond/ai-transition-lab/designs/README.md)

## 注意事项

- `.env`、真实密钥、远端仓库凭据都不得提交
- 演示数据为脱敏虚构数据
- 商品图素材必须可替换且来源可追溯
- 当前已补齐 Pencil 导出图，但 `.pen` 原文件仍未纳入固定仓库路径
