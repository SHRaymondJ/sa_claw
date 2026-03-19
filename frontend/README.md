# 缦序导购工作台前端

这是移动端优先的导购工作台前端工程。

## 关键结构

- `src/App.tsx`
  主页面、解释页和工作台状态管理
- `src/components/renderer-registry.tsx`
  协议组件到本地 React 组件的映射入口
- `src/lib/action-registry.ts`
  协议动作到详情查询、任务完成等行为的映射入口
- `src/components/ui/*`
  基于 shadcn/ui 思路维护的本地基础组件
- `e2e/`
  Playwright 端到端验收

## 工作方式

- 后端只返回协议，不直接决定具体组件实现
- 前端先命中 `renderer registry`
- 点击动作后走 `action registry`
- 未注册组件和动作统一降级，不自由执行

## 常用命令

```bash
pnpm test
pnpm build
pnpm exec playwright test
```
