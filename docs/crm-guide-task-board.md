# 服装品牌导购工作台任务板

## 执行说明

- 每个任务都要有目标、依赖、输入输出、测试和验收标准
- 任务完成后再勾选
- 当前仓库尚未配置可写的托管远端，推送步骤需要在远端准备好后补上

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

- [ ] 托管远端仓库创建与推送
- 当前机器已具备 GitHub SSH 访问能力，但没有可直接调用的 GitHub API / `gh` 登录态，也没有现成的托管仓库可推送
