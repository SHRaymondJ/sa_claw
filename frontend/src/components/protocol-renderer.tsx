import {
  ArrowUpRight,
  Clock3,
  Copy,
  ExternalLink,
  ShieldAlert,
  Sparkles,
  Tag,
  UserRound,
} from 'lucide-react'

import type { UIAction, UIComponent } from '@/lib/protocol'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type RendererProps = {
  component: UIComponent
  onAction: (action: UIAction) => void
}

function SectionFrame({
  title,
  eyebrow,
  children,
}: {
  title: string
  eyebrow?: string
  children: React.ReactNode
}) {
  return (
    <Card className="editorial-card overflow-hidden">
      <CardHeader className="border-b border-[var(--line)] bg-[var(--surface)]/88">
        {eyebrow ? <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--muted)]">{eyebrow}</p> : null}
        <CardTitle className="font-serif-display text-[24px] font-normal">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-0">{children}</CardContent>
    </Card>
  )
}

function RowMeta({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
      {icon}
      <span>{label}</span>
    </div>
  )
}

function RenderCustomerList({ component, onAction }: RendererProps) {
  const items = (component.props.items as Array<Record<string, unknown>>) ?? []
  return (
    <SectionFrame title={component.title} eyebrow="客户清单">
      <div className="divide-y divide-[var(--line)]">
        {items.map((item) => {
          const customerId = String(item.id)
          return (
            <button
              key={customerId}
              className="protocol-row group"
              onClick={() =>
                onAction({
                  action_type: 'open_customer',
                  label: '查看客户详情',
                  entity_type: 'customer',
                  entity_id: customerId,
                  method: 'GET',
                  variant: 'secondary',
                  payload: {},
                })
              }
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-3">
                  <RowMeta icon={<UserRound className="h-4 w-4" />} label="客户后链路" />
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-lg font-medium text-[var(--ink)]">{String(item.name)}</span>
                      <Badge variant="dark">{String(item.tier)}</Badge>
                    </div>
                    <p className="text-sm leading-6 text-[var(--muted)]">{String(item.profile)}</p>
                  </div>
                </div>
                <ArrowUpRight className="mt-1 h-4 w-4 text-[var(--muted)] transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </div>
              <p className="mt-4 text-sm leading-7 text-[var(--ink)]">{String(item.reason)}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {((item.tags as string[]) ?? []).slice(0, 3).map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
              </div>
              <div className="mt-4 border-t border-[var(--line)] pt-4 text-sm leading-6 text-[var(--muted)]">{String(item.next_action)}</div>
            </button>
          )
        })}
      </div>
    </SectionFrame>
  )
}

function RenderProductGrid({ component, onAction }: RendererProps) {
  const items = (component.props.items as Array<Record<string, unknown>>) ?? []
  return (
    <SectionFrame title={component.title} eyebrow="有货推荐">
      <div className="grid gap-px bg-[var(--line)] md:grid-cols-2">
        {items.map((item) => {
          const productId = String(item.id)
          return (
            <button
              key={productId}
              className="group flex flex-col gap-4 bg-[var(--paper)] p-4 text-left transition-[background,transform] duration-300 hover:bg-[var(--surface)]"
              onClick={() =>
                onAction({
                  action_type: 'open_product',
                  label: '查看商品详情',
                  entity_type: 'product',
                  entity_id: productId,
                  method: 'GET',
                  variant: 'secondary',
                  payload: {},
                })
              }
            >
              <div className="relative aspect-[4/5] overflow-hidden border border-[var(--line)] bg-[var(--surface)]">
                <img
                  src={String(item.image_url)}
                  alt={String(item.name)}
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                />
                <div className="absolute inset-x-0 bottom-0 bg-[linear-gradient(180deg,transparent,rgba(23,21,17,0.82))] px-3 py-3">
                  <div className="flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.16em] text-white/78">
                    <span>{String(item.category)}</span>
                    <span>{String(item.color)}</span>
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <p className="font-serif-display text-[24px] leading-none text-[var(--ink)]">{String(item.name)}</p>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium text-[var(--ink)]">¥{String(item.price)}</span>
                  <Badge variant="accent">{String(item.availability)}</Badge>
                </div>
                <p className="text-sm leading-6 text-[var(--muted)]">{String(item.match_reason ?? item.summary ?? '')}</p>
                <div className="flex flex-wrap gap-2">
                  {((item.display_tags as string[]) ?? []).map((tag) => (
                    <Badge key={`${productId}-${tag}`}>{tag}</Badge>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between gap-3 border-t border-[var(--line)] pt-3 text-sm text-[var(--muted)]">
                <span>点击查看尺码、库存与推荐搭配</span>
                <ExternalLink className="h-4 w-4" />
              </div>
            </button>
          )
        })}
      </div>
    </SectionFrame>
  )
}

function RenderTaskList({ component, onAction }: RendererProps) {
  const items = (component.props.items as Array<Record<string, unknown>>) ?? []
  return (
    <SectionFrame title={component.title} eyebrow="任务闭环">
      <div className="divide-y divide-[var(--line)]">
        {items.map((item) => {
          const taskId = String(item.id)
          const isDone = String(item.status) === 'done'
          return (
            <div key={taskId} className="protocol-row space-y-4">
              <div className="flex items-start justify-between gap-4">
                <button
                  className="space-y-2 text-left"
                  onClick={() =>
                    onAction({
                      action_type: 'open_task',
                      label: '查看任务详情',
                      entity_type: 'task',
                      entity_id: taskId,
                      method: 'GET',
                      variant: 'secondary',
                      payload: {},
                    })
                  }
                >
                  <RowMeta icon={<Clock3 className="h-4 w-4" />} label="任务后链路" />
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-medium text-[var(--ink)]">{String(item.task_type)}</span>
                    <Badge variant={String(item.priority) === '高' ? 'dark' : 'accent'}>{String(item.priority)}</Badge>
                  </div>
                  <p className="text-sm leading-6 text-[var(--muted)]">
                    {String(item.customer_name)} · 截止 {String(item.due_date)}
                  </p>
                </button>
                <Button
                  size="sm"
                  variant={isDone ? 'ghost' : 'primary'}
                  disabled={isDone}
                  onClick={() =>
                    onAction({
                      action_type: 'complete_task',
                      label: '完成任务',
                      entity_type: 'task',
                      entity_id: taskId,
                      method: 'POST',
                      variant: 'primary',
                      payload: {},
                    })
                  }
                >
                  {isDone ? '已完成' : '完成'}
                </Button>
              </div>
              <p className="text-sm leading-7 text-[var(--ink)]">{String(item.reason)}</p>
            </div>
          )
        })}
      </div>
    </SectionFrame>
  )
}

function RenderMessageDraft({ component }: { component: UIComponent }) {
  const text = String(component.props.text ?? '')
  return (
    <SectionFrame title={component.title} eyebrow="可直接发送">
      <div className="space-y-4 p-4">
        <div className="border border-[var(--line)] bg-[linear-gradient(180deg,rgba(244,240,231,0.8),rgba(255,255,255,0.96))] p-5 text-sm leading-7 text-[var(--ink)]">
          {text}
        </div>
        <Button size="sm" variant="secondary" onClick={() => navigator.clipboard?.writeText(text)}>
          <Copy className="h-4 w-4" />
          复制话术
        </Button>
      </div>
    </SectionFrame>
  )
}

function RenderTrace({ component }: { component: UIComponent }) {
  const items = (component.props.items as Array<Record<string, unknown>>) ?? []
  return (
    <SectionFrame title={component.title} eyebrow="过程可解释">
      <div className="space-y-0">
        {items.map((item, index) => (
          <div key={`${component.component_id}-${index}`} className="relative p-4 pl-10">
            {index < items.length - 1 ? <div className="absolute bottom-0 left-[20px] top-[32px] w-px bg-[var(--line)]" /> : null}
            <Sparkles className="absolute left-4 top-5 h-4 w-4 text-[var(--muted)]" />
            <p className="text-sm font-medium text-[var(--ink)]">{String(item.label)}</p>
            <p className="mt-1 text-sm leading-6 text-[var(--muted)]">{String(item.detail)}</p>
          </div>
        ))}
      </div>
    </SectionFrame>
  )
}

function RenderSafetyNotice({ component }: { component: UIComponent }) {
  const examples = (component.props.examples as string[]) ?? []
  return (
    <Card className="border-[var(--warning)] bg-[var(--warning-soft)] shadow-[var(--shadow-soft)]">
      <CardHeader>
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-[var(--ink)]" />
          <CardTitle className="font-serif-display text-[24px] font-normal">{component.title}</CardTitle>
        </div>
        <CardDescription>{String(component.props.reason ?? '')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {examples.map((example) => (
          <div key={example} className="soft-panel bg-[var(--paper)] px-3 py-3 text-sm leading-6 text-[var(--ink)]">
            {example}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function RenderDetailKv({ component }: { component: UIComponent }) {
  const items = (component.props.items as Array<Record<string, string>>) ?? []
  return (
    <SectionFrame title={component.title}>
      <div className="divide-y divide-[var(--line)]">
        {items.map((item) => (
          <div key={item.label} className="grid grid-cols-[100px_minmax(0,1fr)] gap-4 p-4 text-sm md:grid-cols-[120px_minmax(0,1fr)]">
            <span className="text-[var(--muted)]">{item.label}</span>
            <span className="text-right leading-6 text-[var(--ink)]">{item.value}</span>
          </div>
        ))}
      </div>
    </SectionFrame>
  )
}

function RenderTagGroup({ component }: { component: UIComponent }) {
  const items = (component.props.items as string[]) ?? []
  return (
    <SectionFrame title={component.title}>
      <div className="flex flex-wrap gap-2 p-4">
        {items.map((item) => (
          <Badge key={item} className="inline-flex items-center gap-1">
            <Tag className="h-3 w-3" />
            {item}
          </Badge>
        ))}
      </div>
    </SectionFrame>
  )
}

function RenderTimeline({ component }: { component: UIComponent }) {
  const items = (component.props.items as Array<Record<string, string>>) ?? []
  return (
    <SectionFrame title={component.title}>
      <div className="space-y-0">
        {items.map((item, index) => (
          <div key={`${component.component_id}-${index}`} className="relative p-4 pl-10">
            {index < items.length - 1 ? <div className="absolute bottom-0 left-[18px] top-[32px] w-px bg-[var(--line)]" /> : null}
            <div className="absolute left-3 top-4 h-3 w-3 border border-[var(--line-strong)] bg-[var(--paper)]" />
            <div className="flex items-start justify-between gap-3 text-sm">
              <div className="space-y-1">
                <p className="font-medium text-[var(--ink)]">{item.channel}</p>
                <p className="leading-6 text-[var(--muted)]">{item.summary}</p>
              </div>
              <span className="whitespace-nowrap text-[var(--muted)]">{new Date(item.created_at).toLocaleDateString('zh-CN')}</span>
            </div>
          </div>
        ))}
      </div>
    </SectionFrame>
  )
}

function RenderImagePanel({ component }: { component: UIComponent }) {
  return (
    <SectionFrame title={component.title}>
      <div className="aspect-[4/5] overflow-hidden border-t border-[var(--line)] bg-[var(--surface)]">
        <img
          src={String(component.props.image_url)}
          alt={String(component.props.alt ?? component.title)}
          className="h-full w-full object-cover"
        />
      </div>
    </SectionFrame>
  )
}

function RenderUnknown({ component }: { component: UIComponent }) {
  return (
    <Card className="border-dashed">
      <CardHeader>
        <CardTitle>未注册组件</CardTitle>
        <CardDescription>{component.component_type}</CardDescription>
      </CardHeader>
    </Card>
  )
}

export function ProtocolRenderer({ component, onAction }: RendererProps) {
  switch (component.component_type) {
    case 'customer_list':
      return <RenderCustomerList component={component} onAction={onAction} />
    case 'product_grid':
      return <RenderProductGrid component={component} onAction={onAction} />
    case 'task_list':
      return <RenderTaskList component={component} onAction={onAction} />
    case 'message_draft':
      return <RenderMessageDraft component={component} />
    case 'trace_timeline':
      return <RenderTrace component={component} />
    case 'safety_notice':
      return <RenderSafetyNotice component={component} />
    case 'detail_kv':
      return <RenderDetailKv component={component} />
    case 'tag_group':
      return <RenderTagGroup component={component} />
    case 'timeline':
      return <RenderTimeline component={component} />
    case 'image_panel':
      return <RenderImagePanel component={component} />
    default:
      return <RenderUnknown component={component} />
  }
}
