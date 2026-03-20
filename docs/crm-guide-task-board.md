# 服装品牌导购工作台任务板

## 执行说明

- 每个任务都要有目标、依赖、输入输出、测试和验收标准
- 任务完成后再勾选
- 严格遵守 `SDD + TDD`
- 一个小任务完成后立刻跑对应测试，不允许攒着一起测
- 当前工程主线改为：`develop -> test -> main`

## 当前版本基线

- 当前基线版本：`v0.1.0`
- 当前版本目标：先把工程文档、分支流转、发布门禁和问题记录机制落到仓库，作为后续 `v1.0.0` 的执行基线

## `v0.1.0` 工程基线任务

### 任务 `0.1.1` 文档体系落地

- [x] 目标：补齐路线图、发布计划、SDD、TDD、分支规范、测试策略、观测策略、UI schema、skills 学习治理文档
- 依赖：无
- 输入输出：新增 `docs/roadmap`、`docs/engineering`、`docs/product`、`docs/reviews`
- 涉及页面/接口：无
- 测试：文档完整性检查
- 验收标准：计划中的文档全部入仓库且互相可引用
- 提交说明：`docs: add commercialization engineering docs`

### 任务 `0.1.2` 分支与远端初始化

- [ ] 目标：建立 `main`、`develop`、`test` 分支和远端仓库映射
- 依赖：任务 `0.1.1`
- 输入输出：本地分支、远端 `origin`、首轮推送
- 涉及页面/接口：无
- 测试：`git branch -a`、`git remote -v`
- 验收标准：三条主分支和远端都可见
- 提交说明：`chore: initialize git flow branches`

### 任务 `0.1.3` 基线测试与发布

- [ ] 目标：对当前系统做一轮基线测试，形成 `v0.1.0` 发布记录
- 依赖：任务 `0.1.2`
- 输入输出：测试结果、基线复盘、首个 tag
- 涉及页面/接口：聊天主链路、详情页、动作链路
- 测试：`pytest && pnpm test -- --run && pnpm build && pnpm exec playwright test`
- 验收标准：测试结果有记录，`test` 和 `main` 发布流程跑通
- 提交说明：`test: publish v0.1.0 baseline`

## `v1.0.0` 去写死与工程底座任务

### 任务 `1.0.1` 稳定性契约落地

- [ ] 目标：定义稳定型问题、生成型问题、重复提问策略和换批条件
- 依赖：`v0.1.0`
- 输入输出：技术设计、测试策略、内部契约更新
- 涉及页面/接口：聊天主链路
- 测试：后端单测 + 集成测试
- 验收标准：系统正式区分“实体稳定”和“文本可变”
- 提交说明：`feat(core): add stability contract`

### 任务 `1.0.2` 去硬编码

- [ ] 目标：把默认数量、样本数、快捷提示、默认品牌门店导购等从实现层迁出
- 依赖：`1.0.1`
- 输入输出：配置层、策略层
- 涉及页面/接口：聊天接口、bootstrap
- 测试：后端单测 + 集成测试
- 验收标准：关键业务行为不再靠代码常量直接决定
- 提交说明：`refactor(core): remove hardcoded business defaults`

### 任务 `1.0.3` 决策分层重构

- [ ] 目标：拆清协议固定层、业务策略层、实体决策层、生成表达层、会话策略层
- 依赖：`1.0.2`
- 输入输出：服务边界重构
- 涉及页面/接口：聊天接口
- 测试：后端集成测试
- 验收标准：核心决策链可解释、可测试、可替换
- 提交说明：`refactor(core): split decision pipeline`

### 任务 `1.0.4` 现有测试去写死

- [ ] 目标：替换固定组件组合和固定顺序断言
- 依赖：`1.0.1`
- 输入输出：测试重构
- 涉及页面/接口：后端测试、前端测试、E2E
- 测试：全套测试
- 验收标准：测试口径和商业化目标一致
- 提交说明：`test: relax brittle demo assertions`

## 任务 1：仓库重定位

- [x] 目标：将仓库从教学项目切换为纯产品仓库
- 依赖：无
- 输入输出：迁出教学文件，重写根文档和仓库规则
- 涉及页面/接口：无
- 测试：确认教学文件已迁出当前仓库
- 验收标准：README、AGENTS、.gitignore 已改为产品仓库语义
- 提交说明：`chore: reposition repository as crm product workspace`

## 任务 2：规格与阻塞登记

- [x] 目标：补齐 PRD、技术设计和任务板，并记录外部阻塞
- 依赖：任务 1
- 输入输出：产出三份文档
- 涉及页面/接口：解释页文案来源
- 测试：文档存在且包含更新机制、一二期边界和外部阻塞
- 验收标准：`docs/` 下三份文档齐全
- 提交说明：`docs: add prd tech design and task board`

## 任务 3：前端工程初始化

- [x] 目标：建立 React/Vite/Tailwind/shadcn/ui 工程与测试骨架
- 依赖：任务 2
- 输入输出：`frontend/` 目录、design token、基础布局、Vitest
- 涉及页面/接口：`/crm`
- 测试：`pnpm test`
- 验收标准：前端可构建、基础页面可加载
- 提交说明：`feat(frontend): scaffold crm workspace`

## 任务 4：数据库与种子数据

- [x] 目标：建立 SQLite schema 与中等演示级种子数据
- 依赖：任务 2
- 输入输出：建表脚本、初始化逻辑、图片来源字段
- 涉及页面/接口：客户详情、商品详情、任务列表
- 测试：后端集成测试
- 验收标准：数据库初始化后可查到客户、商品、任务数据
- 提交说明：`feat(data): add sqlite schema and seed data`

## 任务 5：导购域 API 与受限问答

- [x] 目标：实现 CRM API、意图网关、拒答策略、缓存和长度保护
- 依赖：任务 4
- 输入输出：聊天发送、客户详情、商品详情、任务完成、解释接口
- 涉及页面/接口：全部 CRM API
- 测试：`pytest`
- 验收标准：导购域问题通过，越界问题拒答
- 提交说明：`feat(api): add constrained crm workflow`

## 任务 6：协议 renderer 与主界面

- [x] 目标：实现消息流、卡片、详情抽屉、PC 兼容布局和真实动作链路
- 依赖：任务 3、任务 5
- 输入输出：主聊天页、renderer registry、action registry
- 涉及页面/接口：`/crm`
- 测试：Vitest + API 联调
- 验收标准：点击客户、商品、任务卡都能打开详情或执行动作
- 提交说明：`feat(ui): build mobile-first crm workbench`

## 任务 7：解释页与验收

- [x] 目标：产出解释页并完成单测、集成测、E2E
- 依赖：任务 6
- 输入输出：解释页、E2E 脚本、验收记录
- 涉及页面/接口：`/crm/explain`
- 测试：`pytest && pnpm test && pnpm test:e2e`
- 验收标准：关键流程通过，解释页可用于讲解
- 提交说明：`test: finalize crm demo acceptance`

## 任务 8：Pencil 正式稿与导出

- [x] 目标：补齐移动端、详情层、拒答态、PC 兼容和说明页正式设计稿
- 依赖：任务 2、任务 6
- 输入输出：Pencil 设计稿、导出 PNG 交付物、设计说明索引
- 涉及页面/接口：`/crm`、详情抽屉、拒答态、解释页
- 测试：逐张截图核验 + 导出文件检查
- 验收标准：`designs/pencil-exports/` 下存在 5 张正式导出图，且与当前产品结构一致
- 提交说明：`docs: add pencil deliverables`

## 当前外部阻塞

- [x] `origin` 远端接入与首轮推送
- 目标远端：`git@github.com:SHRaymondJ/sa_claw.git`

## `v0.1.0` 当前测试结果

- [x] `pytest`：`30 passed`
- [x] `pnpm test -- --run`：`12 passed`
- [x] `pnpm build`：passed
- [x] `pnpm exec playwright test`：`14 passed`
- [ ] `test` 分支回归发布
- [ ] `main` 分支发布与线上回归

## 稳定化基线

- [x] 已建立聊天稳定化内部契约：`question_type`、`response_shape`、`context_resolution`、`session_snapshot`
- [x] 已把最近返回形态与最近实体写入会话状态，便于回看与排障
- [x] 已补充真人乱问回归清单：`docs/crm-chat-regression-checklist.md`
- [x] 后续每次改动聊天主链路，必须同时更新：
  - 后端集成测试
  - 前端/E2E 回归
  - 技术设计中的响应形态约束表
