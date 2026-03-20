import type { DetailResponse, UIAction } from '@/lib/protocol'
import { resolveRenderer } from '@/components/renderer-registry'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { useMediaQuery } from '@/hooks/use-media-query'

type DetailPanelProps = {
  detail: DetailResponse | null
  open: boolean
  loading?: boolean
  errorMessage?: string | null
  onRetry?: (() => void) | null
  onOpenChange: (open: boolean) => void
  onAction: (action: UIAction) => void
}

function DetailLoadingState() {
  return (
    <div className="space-y-4">
      <div className="soft-panel shimmer-panel p-5">
        <div className="skeleton-line h-3 w-[72px]" />
        <div className="mt-4 skeleton-line h-8 w-1/2" />
        <div className="mt-3 skeleton-line h-4 w-3/4" />
      </div>
      <div className="soft-panel shimmer-panel p-5">
        <div className="skeleton-line h-3 w-16" />
        <div className="mt-4 space-y-3">
          <div className="skeleton-block h-20" />
          <div className="skeleton-block h-20" />
          <div className="skeleton-block h-28" />
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="soft-panel flex h-full items-center justify-center p-6 text-center">
      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">详情区</p>
        <h3 className="font-serif-display text-2xl text-[var(--ink)]">等待选择实体</h3>
        <p className="max-w-sm text-sm leading-6 text-[var(--muted)]">
          点击客户、商品或任务卡片后，这里会展开对应详情、行动建议和后续动作。
        </p>
      </div>
    </div>
  )
}

function DetailBody({
  detail,
  loading = false,
  errorMessage = null,
  onRetry = null,
  onAction,
}: {
  detail: DetailResponse | null
  loading?: boolean
  errorMessage?: string | null
  onRetry?: (() => void) | null
  onAction: (action: UIAction) => void
}) {
  if (loading) {
    return <DetailLoadingState />
  }

  if (errorMessage) {
    return (
      <div className="soft-panel space-y-3 p-5">
        <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">详情加载失败</p>
        <p className="text-sm leading-6 text-[var(--ink)]">{errorMessage}</p>
        {onRetry ? (
          <button
            type="button"
            className="border border-[var(--line-strong)] bg-[var(--paper)] px-3 py-2 text-sm text-[var(--ink)] transition-colors hover:bg-[var(--surface)]"
            onClick={onRetry}
          >
            重试查看详情
          </button>
        ) : null}
      </div>
    )
  }

  if (!detail) {
    return <EmptyState />
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="detail-hero-card">
        <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{detail.entity_type}</p>
        <h2 className="mt-3 font-serif-display text-[30px] leading-none text-[var(--ink)]">{detail.title}</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">{detail.subtitle}</p>
        <p className="mt-5 text-sm leading-7 text-[var(--ink)]">{detail.summary}</p>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-3 pb-4">
          {detail.ui_schema.map((component) => (
            <DetailRenderer key={component.component_id} component={component} onAction={onAction} />
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

function DetailRenderer({
  component,
  onAction,
}: {
  component: DetailResponse['ui_schema'][number]
  onAction: (action: UIAction) => void
}) {
  const Renderer = resolveRenderer(component.component_type)
  return <Renderer component={component} onAction={onAction} />
}

export function DetailPanel({
  detail,
  open,
  loading = false,
  errorMessage = null,
  onRetry = null,
  onOpenChange,
  onAction,
}: DetailPanelProps) {
  const isDesktop = useMediaQuery('(min-width: 1024px)')

  if (isDesktop) {
    return (
      <div className="sticky top-5 h-[calc(100vh-2.5rem)]">
        <div className="detail-shell h-full p-4">
          <div className="border-b border-[var(--line)] pb-4">
            <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">实体后链路</p>
            <h2 className="mt-2 font-serif-display text-[28px] leading-none text-[var(--ink)]">
              {loading ? '正在展开详情' : detail?.title ?? '右侧详情区'}
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              {loading ? '正在查询实体字段、最近互动与动作建议。' : detail?.subtitle ?? '选中客户、商品或任务后，这里会保持常驻。'}
            </p>
          </div>
          <div className="mt-4 h-[calc(100%-6rem)]">
            <DetailBody detail={detail} loading={loading} errorMessage={errorMessage} onRetry={onRetry} onAction={onAction} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="flex h-[86vh] flex-col">
        <SheetHeader>
          <SheetTitle>{loading ? '正在展开详情' : detail?.title ?? '详情面板'}</SheetTitle>
          <SheetDescription>
            {loading ? '正在查询实体字段、最近互动与动作建议。' : detail?.subtitle ?? '查看实体详情与关联动作'}
          </SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 p-4">
          <DetailBody detail={detail} loading={loading} errorMessage={errorMessage} onRetry={onRetry} onAction={onAction} />
        </div>
      </SheetContent>
    </Sheet>
  )
}
