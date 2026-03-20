import {
  Check,
  ArrowUpRight,
  Copy,
  ExternalLink,
  ListChecks,
  MoveRight,
  NotebookPen,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  Tag,
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
    <Card className="overflow-hidden border-[var(--line)] bg-[var(--paper)] shadow-none">
      <CardHeader className="border-b border-[var(--line)] bg-[var(--paper)] px-4 py-3">
        {eyebrow ? <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted)]">{eyebrow}</p> : null}
        <CardTitle className="text-[15px] font-medium leading-6 text-[var(--ink)]">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-0">{children}</CardContent>
    </Card>
  )
}

function RenderCustomerSpotlight({ component, onAction }: RendererProps) {
  const item = (component.props.item as Record<string, unknown>) ?? {}
  const customerId = String(item.id ?? '')
  return (
    <button
      className="w-full border border-[var(--line)] bg-[var(--paper)] px-3.5 py-3 text-left transition-colors hover:bg-[var(--surface)]"
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
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-[15px] font-medium text-[var(--ink)]">{String(item.name ?? '')}</span>
            <Badge variant="dark">{String(item.tier ?? '')}</Badge>
          </div>
          <p className="text-[12px] leading-5 text-[var(--muted)]">{String(item.profile ?? '')}</p>
        </div>
        <MoveRight className="mt-0.5 h-4 w-4 shrink-0 text-[var(--muted)]" />
      </div>
      <div className="mt-3 grid gap-3 border-t border-[var(--line)] pt-3 md:grid-cols-[minmax(0,1fr)_220px]">
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">推荐依据</p>
          <p className="text-[13px] leading-6 text-[var(--ink)]">{String(item.reason ?? '')}</p>
        </div>
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">下一步动作</p>
          <p className="text-[13px] leading-6 text-[var(--ink)]">{String(item.next_action ?? '')}</p>
        </div>
      </div>
    </button>
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
              className="group px-4 py-3 text-left transition-colors hover:bg-[var(--surface)]"
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
                <div className="space-y-2">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[15px] font-medium text-[var(--ink)]">{String(item.name)}</span>
                      <Badge variant="dark">{String(item.tier)}</Badge>
                    </div>
                    <p className="text-[12px] leading-5 text-[var(--muted)]">{String(item.profile)}</p>
                  </div>
                </div>
                <ArrowUpRight className="mt-1 h-4 w-4 text-[var(--muted)] transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </div>
              <p className="mt-3 text-[13px] leading-6 text-[var(--ink)]">{String(item.reason)}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {((item.tags as string[]) ?? []).slice(0, 3).map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
              </div>
              <div className="mt-3 border-t border-[var(--line)] pt-3 text-[12px] leading-5 text-[var(--muted)]">{String(item.next_action)}</div>
            </button>
          )
        })}
      </div>
    </SectionFrame>
  )
}

function RenderCustomerOverview({ component }: { component: UIComponent }) {
  const tierBreakdown = (component.props.tier_breakdown as Array<Record<string, unknown>>) ?? []
  return (
    <SectionFrame title={component.title} eyebrow="客户盘点">
      <div className="grid gap-px bg-[var(--line)] md:grid-cols-[180px_minmax(0,1fr)]">
        <div className="bg-[var(--paper)] px-4 py-3">
          <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">客户总量</p>
          <p className="mt-2 text-[28px] font-medium leading-none text-[var(--ink)]">
            {String(component.props.total_customers ?? '--')}
          </p>
          <p className="mt-2 text-[12px] leading-5 text-[var(--muted)]">
            当前先展示 {String(component.props.sample_limit ?? 4)} 位代表客户
          </p>
        </div>
        <div className="bg-[var(--paper)] px-4 py-3">
          <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">层级分布</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {tierBreakdown.map((item) => (
              <Badge key={String(item.tier)} variant="dark">
                {String(item.tier)} {String(item.count)}
              </Badge>
            ))}
          </div>
        </div>
      </div>
    </SectionFrame>
  )
}

function RenderCategoryOverview({ component }: { component: UIComponent }) {
  const items = (component.props.items as Array<Record<string, unknown>>) ?? []
  return (
    <SectionFrame title={component.title} eyebrow="品类盘点">
      <div className="border-b border-[var(--line)] px-4 py-3">
        <p className="text-[12px] leading-5 text-[var(--muted)]">
          当前共有 {String(component.props.total_categories ?? items.length)} 个可推荐品类
        </p>
      </div>
      <div className="divide-y divide-[var(--line)]">
        {items.map((item) => (
          <div key={String(item.category)} className="flex items-center justify-between gap-4 px-4 py-3">
            <div className="space-y-1">
              <p className="text-[15px] font-medium text-[var(--ink)]">{String(item.category)}</p>
              <p className="text-[12px] leading-5 text-[var(--muted)]">
                商品 {String(item.product_count)} 款 · 门店现货 {String(item.store_stock)} 件
              </p>
            </div>
            <Badge variant="dark">{String(item.product_count)} 款</Badge>
          </div>
        ))}
      </div>
    </SectionFrame>
  )
}

function RenderProductGrid({ component, onAction }: RendererProps) {
  const items = (component.props.items as Array<Record<string, unknown>>) ?? []
  return (
    <SectionFrame title={component.title} eyebrow="有货推荐">
      <div className="grid gap-px bg-[var(--line)] md:grid-cols-2">
        {items.map((item, index) => {
          const productId = String(item.id)
          return (
            <button
              key={productId}
              className="group bg-[var(--paper)] px-3 py-3 text-left transition-colors duration-200 hover:bg-[var(--surface)]"
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
              <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-3">
                <div className="relative aspect-[3/4] overflow-hidden border border-[var(--line)] bg-[var(--surface)]">
                  <img
                    src={String(item.image_url)}
                    alt={String(item.name)}
                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                  />
                </div>
                <div className="min-w-0 space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">推荐 {index + 1}</span>
                        <Badge>{String(item.category)}</Badge>
                        <Badge>{String(item.color)}</Badge>
                      </div>
                      <p className="text-[14px] font-medium leading-6 text-[var(--ink)]">{String(item.name)}</p>
                    </div>
                    <MoveRight className="mt-1 h-4 w-4 shrink-0 text-[var(--muted)]" />
                  </div>
                  <div className="flex items-center gap-2 text-[12px]">
                    <span className="font-medium text-[var(--ink)]">¥{String(item.price)}</span>
                    <Badge variant="accent">{String(item.availability)}</Badge>
                  </div>
                  <p className="text-[12px] leading-5 text-[var(--ink)]">{String(item.match_reason ?? item.summary ?? '')}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {((item.display_tags as string[]) ?? []).map((tag) => (
                      <Badge key={`${productId}-${tag}`}>{tag}</Badge>
                    ))}
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--line)] pt-2 text-[12px] text-[var(--muted)]">
                    <span>
                      门店 {String(item.store_stock ?? '--')} 件 · 仓库 {String(item.warehouse_stock ?? '--')} 件
                    </span>
                    <span className="inline-flex items-center gap-1">
                      查看详情
                      <ExternalLink className="h-3.5 w-3.5" />
                    </span>
                  </div>
                </div>
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
      {items.length === 0 ? (
        <div className="px-4 py-4 text-[13px] leading-6 text-[var(--muted)]">当前没有待处理任务，可以继续发起新的筛选或推荐请求。</div>
      ) : null}
      <div className="divide-y divide-[var(--line)]">
        {items.map((item) => {
          const taskId = String(item.id)
          const isDone = String(item.status) === 'done'
          return (
            <div key={taskId} className="space-y-3 px-4 py-3">
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
                  <div className="flex items-center gap-2">
                    <span className="text-[15px] font-medium text-[var(--ink)]">{String(item.task_type)}</span>
                    <Badge variant={String(item.priority) === '高' ? 'dark' : 'accent'}>{String(item.priority)}</Badge>
                  </div>
                  <p className="text-[12px] leading-5 text-[var(--muted)]">
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
              <p className="text-[13px] leading-6 text-[var(--ink)]">{String(item.reason)}</p>
            </div>
          )
        })}
      </div>
    </SectionFrame>
  )
}

function RenderRelationshipPlan({ component }: { component: UIComponent }) {
  const strategyPoints = (component.props.strategy_points as string[]) ?? []
  const watchouts = (component.props.watchouts as string[]) ?? []
  const memoryNotes = (component.props.memory_notes as string[]) ?? []
  const messageSeed = String(component.props.message_seed ?? '')
  return (
    <SectionFrame title={component.title} eyebrow="关系维护">
      <div className="space-y-0">
        <div className="grid gap-3 border-b border-[var(--line)] px-4 py-3 md:grid-cols-[minmax(0,1fr)_168px_168px]">
          <div>
            <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">偏好摘要</p>
            <p className="mt-1 text-[13px] leading-6 text-[var(--ink)]">{String(component.props.preferred_summary ?? '')}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">建议渠道</p>
            <p className="mt-1 text-[13px] leading-6 text-[var(--ink)]">{String(component.props.channel ?? '')}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">建议语气</p>
            <p className="mt-1 text-[13px] leading-6 text-[var(--ink)]">{String(component.props.tone ?? '')}</p>
          </div>
        </div>

        <div className="grid gap-px bg-[var(--line)] md:grid-cols-2">
          <div className="bg-[var(--paper)] px-4 py-3">
            <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">维护打法</p>
            <div className="mt-2 space-y-2">
              {strategyPoints.map((item, index) => (
                <div key={item} className="flex gap-2 text-[13px] leading-6 text-[var(--ink)]">
                  <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center border border-[var(--line)] text-[11px] text-[var(--muted)]">
                    {index + 1}
                  </span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-[var(--paper)] px-4 py-3">
            <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">注意点</p>
            <div className="mt-2 space-y-2">
              {watchouts.map((item) => (
                <p key={item} className="text-[13px] leading-6 text-[var(--ink)]">
                  {item}
                </p>
              ))}
            </div>
          </div>
        </div>

        {memoryNotes.length > 0 ? (
          <div className="border-b border-[var(--line)] px-4 py-3">
            <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">长期记忆</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {memoryNotes.map((item) => (
                <Badge key={item}>{item}</Badge>
              ))}
            </div>
          </div>
        ) : null}

        <div className="px-4 py-3">
          <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">建议开场</p>
          <p className="mt-2 text-[13px] leading-6 text-[var(--ink)]">{messageSeed}</p>
        </div>
      </div>
    </SectionFrame>
  )
}

function RenderKnowledgeBriefs({ component }: { component: UIComponent }) {
  const items = (component.props.items as Array<Record<string, string>>) ?? []
  return (
    <SectionFrame title={component.title} eyebrow="经验沉淀">
      <div className="divide-y divide-[var(--line)]">
        {items.map((item, index) => (
          <div key={`${item.source}-${index}`} className="space-y-2 px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                {item.topic === 'relationship_maintenance' ? '客户维护' : '商品推荐'}
              </p>
              <Badge>{item.source}</Badge>
            </div>
            <p className="text-[13px] leading-6 text-[var(--ink)]">{item.content}</p>
          </div>
        ))}
      </div>
    </SectionFrame>
  )
}

function RenderWorkflowCheckpoint({ component }: { component: UIComponent }) {
  const notes = (component.props.notes as string[]) ?? []
  return (
    <SectionFrame title={component.title} eyebrow="执行节奏">
      <div className="space-y-0">
        <div className="grid gap-3 border-b border-[var(--line)] px-4 py-3 md:grid-cols-[minmax(0,1fr)_160px]">
          <div>
            <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">当前目标</p>
            <p className="mt-1 text-[13px] leading-6 text-[var(--ink)]">{String(component.props.user_goal ?? '')}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">当前阶段</p>
            <div className="mt-1 flex flex-wrap gap-2">
              <Badge variant="dark">{String(component.props.stage_label ?? '')}</Badge>
              <Badge>{String(component.props.result_summary ?? '')}</Badge>
            </div>
          </div>
        </div>
        <div className="space-y-0">
          {notes.map((item, index) => (
            <div key={`${component.component_id}-${index}`} className="flex gap-3 border-b border-[var(--line)] px-4 py-3 last:border-b-0">
              <ListChecks className="mt-1 h-4 w-4 shrink-0 text-[var(--muted)]" />
              <p className="text-[13px] leading-6 text-[var(--ink)]">{item}</p>
            </div>
          ))}
        </div>
      </div>
    </SectionFrame>
  )
}

function RenderMessageDraft({ component }: { component: UIComponent }) {
  const text = String(component.props.text ?? '')
  return (
    <SectionFrame title={component.title} eyebrow="可直接发送">
      <div className="space-y-3 p-4">
        <div className="border border-[var(--line)] bg-[var(--surface)]/45 p-4 text-[13px] leading-6 text-[var(--ink)]">
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

function RenderMemoryBriefs({ component }: { component: UIComponent }) {
  const items = (component.props.items as Array<Record<string, string>>) ?? []
  return (
    <SectionFrame title={component.title}>
      <div className="divide-y divide-[var(--line)]">
        {items.map((item, index) => (
          <div key={`${component.component_id}-${index}`} className="space-y-2 px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="dark">{String(item.note_type ?? '')}</Badge>
              <Badge>{String(item.source ?? '')}</Badge>
              <Badge>{String(item.confidence ?? '')}</Badge>
            </div>
            <div className="flex gap-3">
              <NotebookPen className="mt-1 h-4 w-4 shrink-0 text-[var(--muted)]" />
              <p className="text-[13px] leading-6 text-[var(--ink)]">{String(item.content ?? '')}</p>
            </div>
          </div>
        ))}
      </div>
    </SectionFrame>
  )
}

function RenderMemorySuggestions({ component, onAction }: RendererProps) {
  const items = (component.props.items as Array<Record<string, string>>) ?? []
  if (items.length === 0) {
    return null
  }

  return (
    <SectionFrame title={component.title} eyebrow="需确认后入库">
      <div className="divide-y divide-[var(--line)]">
        {items.map((item) => {
          const suggestionId = String(item.id ?? '')
          const customerId = String(item.customer_id ?? '')
          return (
            <div key={suggestionId} className="space-y-3 px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="dark">{String(item.note_type ?? '')}</Badge>
                <Badge>{String(item.source ?? '')}</Badge>
                <Badge>{String(item.confidence ?? '')}</Badge>
              </div>
              <p className="text-[13px] leading-6 text-[var(--ink)]">{String(item.content ?? '')}</p>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() =>
                    onAction({
                      action_type: 'approve_memory_suggestion',
                      label: '转为长期记录',
                      entity_type: 'memory_suggestion',
                      entity_id: suggestionId,
                      method: 'POST',
                      variant: 'primary',
                      payload: { customer_id: customerId, suggestion_id: suggestionId },
                    })
                  }
                >
                  <Check className="h-4 w-4" />
                  转为长期记录
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    onAction({
                      action_type: 'reject_memory_suggestion',
                      label: '忽略这条记录',
                      entity_type: 'memory_suggestion',
                      entity_id: suggestionId,
                      method: 'POST',
                      variant: 'ghost',
                      payload: { customer_id: customerId, suggestion_id: suggestionId },
                    })
                  }
                >
                  <RotateCcw className="h-4 w-4" />
                  暂不采用
                </Button>
              </div>
            </div>
          )
        })}
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
          <div key={`${component.component_id}-${index}`} className="relative px-4 py-3 pl-10">
            {index < items.length - 1 ? <div className="absolute bottom-0 left-[20px] top-[32px] w-px bg-[var(--line)]" /> : null}
            <Sparkles className="absolute left-4 top-5 h-4 w-4 text-[var(--muted)]" />
            <p className="text-[13px] font-medium text-[var(--ink)]">{String(item.label)}</p>
            <p className="mt-1 text-[12px] leading-5 text-[var(--muted)]">{String(item.detail)}</p>
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

function RenderClarificationNotice({ component, onAction }: RendererProps) {
  const prompts = (component.props.prompts as string[]) ?? []
  return (
    <Card className="border-[var(--line-strong)] bg-[var(--surface)] shadow-none">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[var(--ink)]" />
          <CardTitle className="text-[18px] font-medium text-[var(--ink)]">{component.title}</CardTitle>
        </div>
        <CardDescription>{String(component.props.reason ?? '')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2.5">
        {prompts.map((prompt, index) => (
          <Button
            key={`${component.component_id}-${index}`}
            type="button"
            variant="secondary"
            className="h-auto w-full justify-start whitespace-normal px-3 py-3 text-left text-[13px] leading-6"
            onClick={() => {
              const action = component.actions[index]
              if (action) {
                onAction(action)
              }
            }}
          >
            {prompt}
          </Button>
        ))}
      </CardContent>
    </Card>
  )
}

function RenderActionResultNotice({ component, onAction }: RendererProps) {
  const status = String(component.props.status ?? 'info')
  const actions = component.actions ?? []
  return (
    <Card className="border-[var(--line)] bg-[var(--surface)] shadow-none">
      <CardHeader>
        <div className="flex items-center gap-2">
          {status === 'success' ? <Check className="h-4 w-4 text-[var(--ink)]" /> : <ShieldAlert className="h-4 w-4 text-[var(--ink)]" />}
          <CardTitle className="text-[16px] font-medium text-[var(--ink)]">{component.title}</CardTitle>
        </div>
        <CardDescription>{String(component.props.message ?? '')}</CardDescription>
      </CardHeader>
      {actions.length > 0 ? (
        <CardContent className="flex flex-wrap gap-2">
          {actions.map((action) => (
            <Button
              key={`${component.component_id}-${action.action_type}-${action.label}`}
              size="sm"
              variant={action.variant}
              onClick={() => onAction(action)}
            >
              {action.label}
            </Button>
          ))}
        </CardContent>
      ) : null}
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

function RenderSessionCheckpointList({ component }: { component: UIComponent }) {
  const items = (component.props.items as Array<Record<string, string>>) ?? []
  return (
    <SectionFrame title={component.title}>
      <div className="space-y-0">
        {items.map((item, index) => (
          <div key={`${component.component_id}-${index}`} className="border-b border-[var(--line)] px-4 py-3 last:border-b-0">
            <div className="flex items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="dark">{String(item.workflow_name ?? '')}</Badge>
                <Badge>{String(item.workflow_stage ?? '')}</Badge>
                {String(item.focus_customer_name ?? '') ? <Badge>{String(item.focus_customer_name)}</Badge> : null}
              </div>
              <span className="text-[11px] text-[var(--muted)]">
                {item.created_at ? new Date(String(item.created_at)).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''}
              </span>
            </div>
            <p className="mt-2 text-[13px] leading-6 text-[var(--ink)]">{String(item.user_goal ?? '')}</p>
            <p className="mt-2 text-[12px] leading-5 text-[var(--muted)]">{String(item.assistant_summary ?? '')}</p>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              <div className="border border-[var(--line)] px-3 py-2 text-[12px] leading-5 text-[var(--ink)]">
                结果规模：{String(item.result_summary ?? '')}
              </div>
              <div className="border border-[var(--line)] px-3 py-2 text-[12px] leading-5 text-[var(--ink)]">
                下一步：{String(item.next_step ?? '')}
              </div>
            </div>
          </div>
        ))}
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
    case 'customer_spotlight':
      return <RenderCustomerSpotlight component={component} onAction={onAction} />
    case 'customer_list':
      return <RenderCustomerList component={component} onAction={onAction} />
    case 'customer_overview':
      return <RenderCustomerOverview component={component} />
    case 'category_overview':
      return <RenderCategoryOverview component={component} />
    case 'product_grid':
      return <RenderProductGrid component={component} onAction={onAction} />
    case 'task_list':
      return <RenderTaskList component={component} onAction={onAction} />
    case 'relationship_plan':
      return <RenderRelationshipPlan component={component} />
    case 'knowledge_briefs':
      return <RenderKnowledgeBriefs component={component} />
    case 'workflow_checkpoint':
      return <RenderWorkflowCheckpoint component={component} />
    case 'message_draft':
      return <RenderMessageDraft component={component} />
    case 'memory_briefs':
      return <RenderMemoryBriefs component={component} />
    case 'memory_suggestions':
      return <RenderMemorySuggestions component={component} onAction={onAction} />
    case 'session_checkpoint_list':
      return <RenderSessionCheckpointList component={component} />
    case 'trace_timeline':
      return <RenderTrace component={component} />
    case 'safety_notice':
      return <RenderSafetyNotice component={component} />
    case 'clarification_notice':
      return <RenderClarificationNotice component={component} onAction={onAction} />
    case 'action_result_notice':
      return <RenderActionResultNotice component={component} onAction={onAction} />
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
