import type { DetailResponse, UIAction } from '@/lib/protocol'
import { resolveRenderer } from '@/components/renderer-registry'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { useMediaQuery } from '@/hooks/use-media-query'

type DetailPanelProps = {
  detail: DetailResponse | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onAction: (action: UIAction) => void
}

function DetailBody({ detail, onAction }: { detail: DetailResponse | null; onAction: (action: UIAction) => void }) {
  if (!detail) {
    return (
      <div className="flex h-full items-center justify-center border border-dashed border-[var(--line)] bg-[var(--paper)] p-6 text-center text-sm leading-6 text-[var(--muted)]">
        点击客户、商品或任务卡片后，这里会展示对应详情和可执行动作。
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border border-[var(--line)] bg-[var(--paper)] p-4">
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">{detail.entity_type}</p>
        <h2 className="mt-2 text-lg font-semibold text-[var(--ink)]">{detail.title}</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">{detail.subtitle}</p>
        <p className="mt-4 text-sm leading-6 text-[var(--ink)]">{detail.summary}</p>
      </div>
      <ScrollArea className="mt-3 h-full">
        <div className="space-y-3 pb-4">
          {detail.ui_schema.map((component) => (
            <DetailRenderer key={component.component_id} component={component} onAction={onAction} />
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

function DetailRenderer({ component, onAction }: { component: DetailResponse['ui_schema'][number]; onAction: (action: UIAction) => void }) {
  const Renderer = resolveRenderer(component.component_type)
  return <Renderer component={component} onAction={onAction} />
}

export function DetailPanel({ detail, open, onOpenChange, onAction }: DetailPanelProps) {
  const isDesktop = useMediaQuery('(min-width: 1024px)')

  if (isDesktop) {
    return <DetailBody detail={detail} onAction={onAction} />
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="flex h-[84vh] flex-col">
        <SheetHeader>
          <SheetTitle>{detail?.title ?? '详情面板'}</SheetTitle>
          <SheetDescription>{detail?.subtitle ?? '查看实体详情与关联动作'}</SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 p-4">
          <DetailBody detail={detail} onAction={onAction} />
        </div>
      </SheetContent>
    </Sheet>
  )
}
