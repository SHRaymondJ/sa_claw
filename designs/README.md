# Pencil 设计交付

当前仓库已经补齐以下正式设计导出图，均由 Pencil 桌面编辑器生成并导出：

- `designs/pencil-exports/GoEJp.png`
  - 移动端主工作台
- `designs/pencil-exports/lJZOy.png`
  - 移动端详情抽屉
- `designs/pencil-exports/LAoMv.png`
  - 移动端拒答态
- `designs/pencil-exports/QIctY.png`
  - PC 端工作台
- `designs/pencil-exports/BhEkG.png`
  - 说明页

## 使用方式

- 页面级更新：先改 Pencil 稿，再更新页面规范、前端布局和 E2E
- 组件级更新：先改 token，再改基础组件，再验证 registry 映射
- 协议级更新：先改 schema 版本与 explain 内容，再验证前端降级行为

## 当前限制

- 当前可稳定导出 PNG 交付物
- Pencil 临时文档未自动保存到仓库内固定 `.pen` 路径，后续如需把原始 `.pen` 文件纳入版本库，需要在桌面端明确保存路径后再接入
