# 缦序导购工作台前端

这是移动端优先的导购工作台前端工程。

## 关键结构

- `src/App.tsx`：页面路由与工作台主体
- `src/components/renderer-registry.tsx`：协议组件到 React 组件的映射
- `src/lib/action-registry.ts`：协议动作到前端行为和 API 的映射
- `src/components/ui/*`：基于 shadcn/ui 思路维护的本地基础组件
- `e2e/`：Playwright 端到端验收

## 常用命令

```bash
pnpm test
pnpm build
pnpm exec playwright test
```
