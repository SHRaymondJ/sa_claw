import { startTransition, useEffect, useRef, useState } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import {
  BotMessageSquare,
  Database,
  GitBranch,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
  Workflow,
} from 'lucide-react'

import { APIError, getBootstrap, getExplain, sendChat, setRequestIdentity } from '@/lib/api'
import { DetailPanel } from '@/components/detail-panel'
import { resolveRenderer } from '@/components/renderer-registry'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { dispatchAction } from '@/lib/action-registry'
import type {
  BootstrapResponse,
  ActionMutationResponse,
  ChatMessage,
  DetailResponse,
  ExplainResponse,
  TaskCompleteResponse,
  UIAction,
} from '@/lib/protocol'
import { cn } from '@/lib/utils'
import { useMediaQuery } from '@/hooks/use-media-query'

const WELCOME_MESSAGE: ChatMessage = {
  message_id: 'system-intro',
  role: 'assistant',
  text: '直接输入客户、商品或跟进目标，我先给结果，再展开详情。',
  created_at: new Date().toISOString(),
  ui_schema: [],
}

const MIN_RESPONSE_DELAY_MS = 520
const EMPTY_STATE_CUSTOMER_ACTION: UIAction = {
  action_type: 'open_customer',
  label: '查看客户详情',
  entity_type: 'customer',
  entity_id: 'C001',
  method: 'GET',
  variant: 'secondary',
  payload: {},
}

function buildSessionAction(sessionId: string): UIAction {
  return {
    action_type: 'open_session',
    label: '查看会话节点',
    entity_type: 'session',
    entity_id: sessionId,
    method: 'GET',
    variant: 'secondary',
    payload: {},
  }
}

function formatTime(iso: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

async function withMinimumDelay<T>(promise: Promise<T>, minimumMs: number): Promise<T> {
  const startedAt = Date.now()
  const result = await promise
  const elapsed = Date.now() - startedAt
  if (elapsed < minimumMs) {
    await new Promise((resolve) => window.setTimeout(resolve, minimumMs - elapsed))
  }
  return result
}

function buildActionResultComponent({
  title,
  message,
  status,
  actions = [],
}: {
  title: string
  message: string
  status: string
  actions?: UIAction[]
}) {
  return {
    component_type: 'action_result_notice',
    component_id: `notice-${Date.now()}`,
    title,
    props: { message, status },
    actions,
  }
}

function BootstrapShell() {
  return (
    <div className="flex min-h-screen flex-col border-x border-[var(--line)] bg-[var(--paper)]">
      <header className="border-b border-[var(--line)] bg-[var(--surface)] px-4 py-5 md:px-6">
        <p className="text-xs uppercase tracking-[0.24em] text-[var(--muted)]">门店工作台</p>
        <h1 className="mt-3 font-serif-display text-3xl text-[var(--ink)]">正在整理今日待办与重点客户</h1>
        <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">
          正在同步导购席位、今日任务和最近高意向客户，稍后会把主工作台完整展开。
        </p>
      </header>
      <div className="grid flex-1 gap-4 px-4 py-5 md:px-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <div className="soft-panel shimmer-panel p-5">
            <div className="skeleton-line h-3 w-24" />
            <div className="mt-4 skeleton-line h-9 w-3/5" />
            <div className="mt-3 skeleton-line h-4 w-4/5" />
            <div className="mt-8 grid gap-3 md:grid-cols-3">
              <div className="skeleton-block h-[88px]" />
              <div className="skeleton-block h-[88px]" />
              <div className="skeleton-block h-[88px]" />
            </div>
          </div>
          <div className="soft-panel p-5">
            <div className="skeleton-line h-4 w-28" />
            <div className="mt-4 space-y-3">
              <div className="skeleton-block h-[120px]" />
              <div className="skeleton-block h-[104px]" />
              <div className="skeleton-block h-32" />
            </div>
          </div>
        </div>
        <div className="hidden lg:block">
          <div className="soft-panel shimmer-panel h-full p-5">
            <div className="skeleton-line h-3 w-20" />
            <div className="mt-4 skeleton-line h-8 w-1/2" />
            <div className="mt-6 space-y-3">
              <div className="skeleton-block h-28" />
              <div className="skeleton-block h-24" />
              <div className="skeleton-block h-40" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function PendingReplyCard() {
  return (
    <div data-pending-reply="true" className="thread-enter max-w-[88%] space-y-2.5 md:max-w-[68%]">
      <div className="message-card shimmer-panel space-y-3 p-3.5 md:p-4">
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-[var(--muted)]">
          <Sparkles className="h-4 w-4" />
          正在整理本次客户建议
        </div>
        <div className="space-y-3">
          <div className="skeleton-line h-4 w-3/4" />
          <div className="skeleton-line h-4 w-5/6" />
          <div className="skeleton-line h-4 w-2/3" />
        </div>
      </div>
      <div className="grid gap-2.5 md:grid-cols-2">
        <div className="soft-panel shimmer-panel p-3.5">
          <div className="skeleton-line h-3 w-16" />
          <div className="mt-3 skeleton-block h-18" />
        </div>
        <div className="soft-panel shimmer-panel p-3.5">
          <div className="skeleton-line h-3 w-20" />
          <div className="mt-3 skeleton-block h-18" />
        </div>
      </div>
    </div>
  )
}

function EmptyWorkbenchState({
  isDesktop,
  prompts,
  onSelectPrompt,
  onOpenCustomer,
}: {
  isDesktop: boolean
  prompts: string[]
  onSelectPrompt: (prompt: string) => void
  onOpenCustomer: () => void
}) {
  const previewPrompts = ['今天优先跟进客户', '通勤西装现货']

  if (isDesktop) {
    return (
      <div className="flex h-full flex-col px-5 py-4">
        <div className="w-full max-w-[520px] space-y-2.5">
          <div className="border border-[var(--line)] bg-[var(--paper)] px-3 py-2 text-[12px] leading-5 text-[var(--ink)]">
            直接输入导购目标，先看结果，再按需展开右侧详情。
          </div>
          <button
            type="button"
            className="w-full border border-[var(--line-strong)] bg-[var(--paper)] px-3 py-2.5 text-left transition-colors hover:bg-[var(--surface)]"
            onClick={onOpenCustomer}
          >
            <p className="text-[12px] font-medium text-[var(--ink)]">结果摘要</p>
            <p className="mt-1.5 text-[12px] leading-5 text-[var(--ink)]">
              推荐客户 3 人 · 有货商品 4 款 · 待执行任务 2 条
              <br />
              聊天区优先承载本轮判断，详情在右侧查看。
            </p>
          </button>
        </div>
        <div className="min-h-0 flex-1" />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col px-4 py-4">
      <div className="space-y-3">
        <div className="border border-[var(--line)] bg-[var(--paper)] px-3 py-3 text-[13px] leading-6 text-[var(--ink)]">
          直接说目标，我会整理客户、商品和下一步动作。
        </div>
        <div className="flex gap-2">
          {previewPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="flat-chip"
              onClick={() => onSelectPrompt(prompt === '今天优先跟进客户' ? prompts[0] ?? prompt : prompts[1] ?? prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
        <button
          type="button"
          aria-label="查看推荐客户详情"
          className="w-full border border-[var(--line-strong)] bg-[var(--paper)] px-3 py-3 text-left transition-colors hover:bg-[var(--surface)]"
          onClick={onOpenCustomer}
        >
          <p className="text-[12px] font-medium text-[var(--ink)]">推荐客户</p>
          <p className="mt-2 text-[13px] leading-6 text-[var(--ink)]">
            林知夏 · 黑金 · 今天优先
            <br />
            打开客户详情后可直接发送私聊草稿
          </p>
        </button>
      </div>
      <div className="min-h-0 flex-1" />
    </div>
  )
}

function MessageBubble({
  message,
  onAction,
}: {
  message: ChatMessage
  onAction: (action: UIAction) => void
}) {
  const isUser = message.role === 'user'
  const isIntro = message.message_id === 'system-intro'
  const statusHint = String(message.meta?.status_hint ?? '')
  const handoffReason = String(message.meta?.handoff_reason ?? '')

  return (
    <div
      data-message-id={message.message_id}
      className={cn('thread-enter group flex items-start gap-2', isUser ? 'justify-end' : 'justify-start')}
    >
      {!isUser && !isIntro ? (
        <Avatar className="mt-0.5 hidden h-7 w-7 border border-[var(--line)] bg-[var(--surface)] md:flex">
          <AvatarFallback>导</AvatarFallback>
        </Avatar>
      ) : null}
      {!isUser ? (
        <div className="hidden pt-2 text-[10px] text-[var(--muted)] opacity-0 transition-opacity duration-200 group-hover:opacity-100 md:block">
          {formatTime(message.created_at)}
        </div>
      ) : null}
      <div className={cn('max-w-[84%] space-y-2 md:max-w-[64%]', isUser ? 'items-end' : 'items-start')}>
        {!isUser && !isIntro && statusHint ? (
          <div className="px-0.5">
            <div className="inline-flex items-center gap-2 border border-[var(--line)] bg-[var(--surface)] px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              <Sparkles className="h-3 w-3" />
              {statusHint}
            </div>
            {handoffReason ? <p className="mt-1 max-w-[420px] text-[11px] leading-5 text-[var(--muted)]">{handoffReason}</p> : null}
          </div>
        ) : null}
        <div
          className={cn(
            'message-card p-2.5 md:p-3',
            isUser ? 'message-card-user' : 'message-card-assistant',
            isIntro ? 'px-3 py-2 md:px-3 md:py-2.5' : undefined,
          )}
        >
          <p
            className={cn(
              'text-[13px] leading-6 md:text-[14px] md:leading-6',
              isUser ? 'text-[var(--paper)]' : 'text-[var(--ink)]',
              isIntro ? 'text-[12px] leading-5 md:text-[13px] md:leading-5' : undefined,
            )}
          >
            {message.text}
          </p>
        </div>
        {message.ui_schema.map((component) => (
          <MessageRenderer key={component.component_id} component={component} onAction={onAction} />
        ))}
      </div>
      {isUser ? (
        <div className="hidden pt-2 text-[10px] text-[var(--muted)] opacity-0 transition-opacity duration-200 group-hover:opacity-100 md:block">
          {formatTime(message.created_at)}
        </div>
      ) : null}
    </div>
  )
}

function ConversationStatusBar({
  snapshot,
  modeLabel,
}: {
  snapshot: Record<string, unknown> | null
  modeLabel: string
}) {
  if (!snapshot) {
    return null
  }

  const currentCustomer = String(snapshot.active_customer_name ?? '') || '未锁定'
  const currentIntent = String(snapshot.active_intent ?? '') || '未识别'
  const responseShape = String(snapshot.last_response_shape ?? '') || '暂无'
  const handoffReason = String(snapshot.handoff_reason ?? '') || '当前等待新的用户目标。'

  return (
    <div
      data-testid="conversation-status-bar"
      className="border-b border-[var(--line)] bg-[var(--surface)] px-4 py-2.5 md:px-5"
    >
      <div className="grid gap-2 md:grid-cols-[repeat(3,minmax(0,1fr))]">
        <div className="border border-[var(--line)] bg-[var(--paper)] px-3 py-2">
          <p className="text-[10px] uppercase tracking-[0.16em] text-[var(--muted)]">当前锁定客户</p>
          <p data-testid="status-customer" className="mt-1 text-[12px] leading-5 text-[var(--ink)]">
            {currentCustomer}
          </p>
        </div>
        <div className="border border-[var(--line)] bg-[var(--paper)] px-3 py-2">
          <p className="text-[10px] uppercase tracking-[0.16em] text-[var(--muted)]">当前任务类型</p>
          <p data-testid="status-task-type" className="mt-1 text-[12px] leading-5 text-[var(--ink)]">
            {modeLabel || currentIntent}
          </p>
        </div>
        <div className="border border-[var(--line)] bg-[var(--paper)] px-3 py-2">
          <p className="text-[10px] uppercase tracking-[0.16em] text-[var(--muted)]">当前结果形态</p>
          <p data-testid="status-response-shape" className="mt-1 line-clamp-2 text-[12px] leading-5 text-[var(--ink)]">
            {responseShape}
          </p>
        </div>
      </div>
      <p data-testid="status-handoff-reason" className="mt-2 text-[11px] leading-5 text-[var(--muted)]">
        本轮切换原因：{handoffReason}
      </p>
    </div>
  )
}

function DesktopPreviewSidebar({ onOpenCustomer }: { onOpenCustomer: () => void }) {
  return (
    <aside className="hidden border-l border-[var(--line)] bg-[var(--paper)] lg:block">
      <div className="h-full px-4 py-3.5">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">详情区</p>
        <button
          type="button"
          aria-label="查看默认客户详情"
          className="mt-3 w-full border border-[var(--line)] bg-[var(--paper)] px-3 py-3 text-left transition-colors hover:bg-[var(--surface)]"
          onClick={onOpenCustomer}
        >
          <p className="text-[15px] font-medium leading-6 text-[var(--ink)]">林知夏</p>
          <p className="mt-1.5 text-[12px] leading-5 text-[var(--ink)]">
            黑金会员 · 近 30 天浏览通勤西装 5 次
            <br />
            建议动作：优先私聊 + 引导试穿预约
            <br />
            这里保持常驻，便于核对实体信息与执行动作。
          </p>
        </button>
      </div>
    </aside>
  )
}

function MessageRenderer({
  component,
  onAction,
}: {
  component: ChatMessage['ui_schema'][number]
  onAction: (action: UIAction) => void
}) {
  const Renderer = resolveRenderer(component.component_type)
  return <Renderer component={component} onAction={onAction} />
}

function ExplainPage() {
  const [payload, setPayload] = useState<ExplainResponse | null>(null)

  useEffect(() => {
    void getExplain().then(setPayload)
  }, [])

  return (
    <div className="min-h-screen bg-[var(--canvas)] px-4 py-6 md:px-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="soft-panel flex items-center justify-between gap-4 px-5 py-5">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">说明页</p>
            <h1 className="mt-2 font-serif-display text-3xl text-[var(--ink)]">{payload?.title ?? '加载中'}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">{payload?.subtitle}</p>
          </div>
          <Button asChild variant="secondary">
            <Link to="/">返回工作台</Link>
          </Button>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="editorial-card">
            <CardHeader>
              <Workflow className="h-5 w-5 text-[var(--muted)]" />
              <CardTitle>协议驱动</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-[var(--muted)]">后端负责返回协议，前端负责渲染与动作绑定。</CardContent>
          </Card>
          <Card className="editorial-card">
            <CardHeader>
              <Database className="h-5 w-5 text-[var(--muted)]" />
              <CardTitle>实体后链路</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-[var(--muted)]">卡片点击后进入客户、商品、任务详情与动作接口。</CardContent>
          </Card>
          <Card className="editorial-card">
            <CardHeader>
              <ShieldCheck className="h-5 w-5 text-[var(--muted)]" />
              <CardTitle>边界保护</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-[var(--muted)]">越界话题先拒答，不进入检索和生成。</CardContent>
          </Card>
          <Card className="editorial-card">
            <CardHeader>
              <GitBranch className="h-5 w-5 text-[var(--muted)]" />
              <CardTitle>维护可持续</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-[var(--muted)]">页面、组件、协议三层分别治理，不混在一起改。</CardContent>
          </Card>
        </div>
        <div className="grid gap-4">
          {payload?.sections.map((section) => (
            <Card key={section.key} className="editorial-card">
              <CardHeader>
                <CardTitle>{section.title}</CardTitle>
                <p className="text-sm leading-6 text-[var(--muted)]">{section.summary}</p>
                <div className="flex flex-wrap gap-2">
                  {section.tags.map((tag) => (
                    <Badge key={tag}>{tag}</Badge>
                  ))}
                </div>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <div className="space-y-3">
                  {section.points.map((point) => (
                    <div key={point} className="soft-panel px-4 py-3 text-sm leading-6 text-[var(--ink)]">
                      {point}
                    </div>
                  ))}
                </div>
                <div className="soft-panel space-y-3 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">落地流程</p>
                  {section.steps.map((step, index) => (
                    <div key={step} className="flex gap-3 text-sm leading-6 text-[var(--ink)]">
                      <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center border border-[var(--line)] bg-[var(--surface)] text-xs">
                        {index + 1}
                      </span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="editorial-card">
            <CardHeader>
              <CardTitle>协议示例</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto border border-[var(--line)] bg-[var(--surface)] p-4 text-xs leading-6 text-[var(--ink)]">
                {JSON.stringify(payload?.protocol_example ?? {}, null, 2)}
              </pre>
            </CardContent>
          </Card>
          <Card className="editorial-card">
            <CardHeader>
              <CardTitle>维护清单</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {payload?.maintenance_checklist.map((item) => (
                <div key={item} className="soft-panel px-4 py-3 text-sm leading-6 text-[var(--ink)]">
                  {item}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
        <Card className="border-[var(--warning)] bg-[var(--warning-soft)] shadow-[var(--shadow-soft)]">
          <CardHeader>
            <CardTitle>当前外部阻塞</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {payload?.blockers.map((item) => (
              <div key={item} className="soft-panel bg-[var(--paper)] px-4 py-3 text-sm leading-6 text-[var(--ink)]">
                {item}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function WorkbenchPage() {
  const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null)
  const [bootstrapLoading, setBootstrapLoading] = useState(true)
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE])
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessionMeta, setSessionMeta] = useState<Record<string, unknown> | null>(null)
  const [detail, setDetail] = useState<DetailResponse | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailRetryAction, setDetailRetryAction] = useState<UIAction | null>(null)
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const messageViewportRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let cancelled = false

    void withMinimumDelay(getBootstrap(), 360)
      .then((payload) => {
        if (cancelled) return
        setRequestIdentity({ advisorId: payload.advisor_id, storeId: payload.store_id })
        setBootstrap(payload)
      })
      .finally(() => {
        if (cancelled) return
        setBootstrapLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const viewport = messageViewportRef.current
    if (!viewport) {
      return
    }

    const frame = window.requestAnimationFrame(() => {
      const pendingNode = viewport.querySelector('[data-pending-reply="true"]')
      if (
        loading &&
        pendingNode instanceof HTMLElement &&
        typeof pendingNode.scrollIntoView === 'function'
      ) {
        pendingNode.scrollIntoView({ behavior: 'smooth', block: 'start' })
        return
      }

      const lastMessage = messages.at(-1)
      if (lastMessage) {
        const messageNode = viewport.querySelector(`[data-message-id="${lastMessage.message_id}"]`)
        if (
          messageNode instanceof HTMLElement &&
          typeof messageNode.scrollIntoView === 'function'
        ) {
          messageNode.scrollIntoView({ behavior: 'smooth', block: 'start' })
          return
        }
      }

      viewport.scrollTop = viewport.scrollHeight
    })

    return () => window.cancelAnimationFrame(frame)
  }, [messages, loading])

  function appendTaskCompletion(payload: TaskCompleteResponse) {
    if (payload.session_meta) {
      setSessionMeta(payload.session_meta as Record<string, unknown>)
    }
    setMessages((current) =>
      current.map((message) => ({
        ...message,
        ui_schema: message.ui_schema.map((component) => {
          if (component.component_type !== 'task_list') {
            return component
          }

          const items = (component.props.items as Array<Record<string, unknown>>).map((item) =>
            String(item.id) === payload.task_id ? { ...item, status: payload.status } : item,
          )

          return {
            ...component,
            props: {
              ...component.props,
              items,
            },
          }
        }),
      })),
    )

    startTransition(() => {
      setMessages((current) => [
        ...current,
        {
          message_id: `assistant-${payload.task_id}`,
          role: 'assistant',
          text: payload.message,
          created_at: new Date().toISOString(),
          ui_schema: [payload.updated_component],
          meta: {
            status_hint: '任务状态已更新',
            handoff_reason: '执行动作已成功落库，当前结果按最新状态刷新。',
          },
        },
      ])
    })
  }

  function appendMutationNotice(payload: ActionMutationResponse) {
    if (payload.session_meta) {
      setSessionMeta(payload.session_meta as Record<string, unknown>)
    }
    if (!payload.updated_component) {
      return
    }
    startTransition(() => {
      setMessages((current) => [
        ...current,
        {
          message_id: `assistant-mutation-${payload.entity_id}-${Date.now()}`,
          role: 'assistant',
          text: payload.message,
          created_at: new Date().toISOString(),
          ui_schema: [payload.updated_component!],
          meta: {
            status_hint: '状态已更新',
            handoff_reason: '当前动作已执行完成。',
          },
        },
      ])
    })
  }

  async function handleSend(nextValue?: string) {
    const content = (nextValue ?? value).trim()
    if (!content || loading) {
      return
    }

    const userMessage: ChatMessage = {
      message_id: `user-${Date.now()}`,
      role: 'user',
      text: content,
      created_at: new Date().toISOString(),
      ui_schema: [],
    }

    startTransition(() => {
      setMessages((current) => [...current, userMessage])
    })
    setValue('')
    setLoading(true)

    try {
      const response = await withMinimumDelay(sendChat(content, sessionId), MIN_RESPONSE_DELAY_MS)
      setSessionId(response.session_id)
      setSessionMeta((response.meta as Record<string, unknown>) ?? null)
      setDetailError(null)
      startTransition(() => {
        const assistantMessage = response.messages.findLast((item) => item.role === 'assistant')
        if (!assistantMessage) {
          return
        }
        setMessages((current) => [...current, assistantMessage])
      })
    } catch (error) {
      const message =
        error instanceof APIError
          ? error.message
          : error instanceof Error
            ? error.message
            : '当前消息发送失败，请稍后重试。'
      startTransition(() => {
        setMessages((current) => [
          ...current,
          {
            message_id: `assistant-error-${Date.now()}`,
            role: 'assistant',
            text: `刚才这条消息没有处理成功。${message}`,
            created_at: new Date().toISOString(),
            ui_schema: [
              buildActionResultComponent({
                title: '发送失败',
                message: '你可以直接重试这条消息，当前输入内容不会丢失。',
                status: 'error',
                actions: [
                  {
                    action_type: 'retry_send',
                    label: '重试发送',
                    entity_type: 'conversation',
                    method: 'POST',
                    variant: 'primary',
                    payload: { message: content },
                  },
                ],
              }),
            ],
            meta: {
              status_hint: '发送失败',
              handoff_reason: '网络或服务暂时不可用，本轮没有写入新的结果。',
            },
          },
        ])
      })
    } finally {
      setLoading(false)
    }
  }

  async function handleAction(action: UIAction) {
    if (action.action_type === 'retry_send') {
      const retryMessage = String(action.payload.message ?? '')
      await handleSend(retryMessage)
      return
    }
    if (action.method === 'GET') {
      setDetail(null)
      setDetailRetryAction(action)
    }
    try {
      await dispatchAction(action, {
        setDetail,
        setDetailOpen,
        setDetailLoading,
        setDetailError,
        setDetailRetryAction,
        setSessionMeta,
        appendTaskCompletion,
        appendMutationNotice,
      })
    } catch (error) {
      const message =
        error instanceof APIError
          ? error.message
          : error instanceof Error
            ? error.message
            : '当前操作执行失败，请稍后重试。'
      if (action.method === 'GET') {
        setDetailOpen(true)
        setDetailError(message)
        return
      }
      startTransition(() => {
        setMessages((current) => [
          ...current,
          {
            message_id: `assistant-action-error-${Date.now()}`,
            role: 'assistant',
            text: `刚才的动作没有执行成功。${message}`,
            created_at: new Date().toISOString(),
            ui_schema: [
              buildActionResultComponent({
                title: '操作失败',
                message: '你可以直接重试刚才的动作，系统不会把失败状态当成成功。',
                status: 'error',
                actions: [action],
              }),
            ],
            meta: {
              status_hint: '操作失败',
              handoff_reason: '本轮变更未成功写入，当前结果保持旧状态。',
            },
          },
        ])
      })
    }
  }

  if (bootstrapLoading) {
    return <BootstrapShell />
  }

  const compactMeta = `${bootstrap?.advisor_name ?? '林顾问'} · ${bootstrap?.store_name ?? '上海静安店'}`
  const compactMetaLine = `${bootstrap?.advisor_name ?? '林顾问'} · ${(bootstrap?.store_name ?? '上海静安店').replace('上海', '')} · 待办 ${bootstrap?.pending_task_count ?? '--'}`
  const desktopMetaLine = `${compactMeta} · 今日待办 ${bootstrap?.pending_task_count ?? '--'}`
  const showEmptyState = messages.length === 1 && !loading

  async function openDefaultCustomerPreview() {
    await handleAction(EMPTY_STATE_CUSTOMER_ACTION)
  }

  return (
    <div className="min-h-[100dvh] bg-[var(--canvas)]">
      <div className="mx-auto flex min-h-[100dvh] max-w-[1460px] flex-col px-0 lg:grid lg:min-h-screen lg:grid-cols-[minmax(0,1fr)_296px] lg:px-5 lg:py-5">
        <main className="relative flex h-[100dvh] min-h-[100dvh] flex-col overflow-hidden border-x border-[var(--line)] bg-[var(--paper)] lg:h-[calc(100vh-2.5rem)] lg:min-h-0 lg:border">
          <header className="border-b border-[var(--line)] bg-[var(--paper)] px-4 py-3.5 md:px-5 md:py-3.5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 space-y-1">
                <div className="flex items-center gap-1.5 text-[9px] uppercase tracking-[0.16em] text-[var(--muted)] md:text-[10px]">
                  <BotMessageSquare className="h-3.5 w-3.5" />
                  门店工作台
                </div>
                <div className="flex items-center justify-between gap-3">
                  <h1 className="truncate font-serif-display text-[17px] leading-none text-[var(--ink)] md:text-[19px]">
                    {bootstrap?.brand_name ?? '缦序'} 导购席位
                  </h1>
                  <Badge variant="dark" className="shrink-0">
                    在线
                  </Badge>
                </div>
                <div className="text-[12px] leading-5 text-[var(--muted)]">
                  {isDesktop ? desktopMetaLine : compactMetaLine}
                </div>
              </div>
            </div>
          </header>

          <ConversationStatusBar
            snapshot={(sessionMeta?.session_snapshot as Record<string, unknown> | null) ?? null}
            modeLabel={String(sessionMeta?.conversation_mode_label ?? '')}
          />

          <div className="relative min-h-0 flex-1 overflow-hidden">
            <div
              ref={messageViewportRef}
              className="min-h-0 h-full overflow-y-auto overscroll-contain scroll-smooth"
            >
              <div className="h-full px-0 py-0">
                {showEmptyState ? (
                  <EmptyWorkbenchState
                    isDesktop={isDesktop}
                    prompts={bootstrap?.quick_prompts ?? []}
                    onSelectPrompt={(prompt) => void handleSend(prompt)}
                    onOpenCustomer={() => void openDefaultCustomerPreview()}
                  />
                ) : (
                  <div className="space-y-3 px-4 py-3 pb-4 md:space-y-3.5 md:px-5 md:py-4 md:pb-5">
                    {messages.map((message) => (
                      <MessageBubble key={message.message_id} message={message} onAction={handleAction} />
                    ))}
                    {loading ? <PendingReplyCard /> : null}
                  </div>
                )}
              </div>
            </div>
          </div>

          <footer
            data-testid="composer-shell"
            className="z-20 shrink-0 border-t border-[var(--line)] bg-[var(--paper)] px-4 py-3 pb-[calc(env(safe-area-inset-bottom)+8px)] md:px-5 md:py-3"
          >
            <div className="border border-[var(--line)] bg-[var(--paper)] px-3 py-2.5">
              {isDesktop ? (
                <div className="space-y-2.5">
                  <Textarea
                    value={value}
                    onChange={(event) => setValue(event.target.value)}
                    className="min-h-[52px] max-h-[96px] resize-none border-0 bg-transparent px-0 py-0 text-[14px] leading-6 focus:border-0 focus-visible:ring-0"
                    placeholder="例如：给最近关注通勤西装的客户挑 3 款有货单品"
                  />
                  <div className="flex items-center justify-between gap-4 border-t border-[var(--line)] pt-2.5">
                    <p className="text-[11px] leading-5 text-[var(--muted)]">支持客户筛选、商品推荐、库存查询、任务处理</p>
                    <div className="flex items-center gap-2">
                      {sessionId ? (
                        <Button
                          variant="secondary"
                          onClick={() => void handleAction(buildSessionAction(sessionId))}
                          className="h-8.5 px-3"
                        >
                          本轮节点
                        </Button>
                      ) : null}
                      <Button
                        variant="primary"
                        onClick={() => void handleSend()}
                        disabled={loading}
                        className="h-8.5 px-4"
                        aria-label="发送"
                      >
                        {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
                        发送
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-2.5">
                  <div className="border-b border-[var(--line)] pb-2.5">
                    <Textarea
                      value={value}
                      onChange={(event) => setValue(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' && !event.shiftKey && !isDesktop) {
                          event.preventDefault()
                          void handleSend()
                        }
                      }}
                      className="min-h-[38px] max-h-[76px] resize-none border-0 bg-transparent px-0 py-0 text-[13px] leading-6 focus:border-0 focus-visible:ring-0"
                      placeholder="例如：找今天该优先联系的高净值客户"
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[10px] leading-4 text-[var(--muted)]">Enter 发送</p>
                    <div className="flex items-center gap-2">
                      {sessionId ? (
                        <Button
                          variant="secondary"
                          onClick={() => void handleAction(buildSessionAction(sessionId))}
                          className="h-10 px-3 text-[12px]"
                        >
                          节点
                        </Button>
                      ) : null}
                      <Button
                        variant="primary"
                        onClick={() => void handleSend()}
                        disabled={loading}
                        className="h-10 min-w-[52px] px-3 text-[13px]"
                        aria-label="发送"
                      >
                        {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
                        发送
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </footer>
        </main>

        {isDesktop ? detail || detailLoading ? (
          <aside className="hidden lg:block">
            <DetailPanel
              detail={detail}
              open={detailOpen}
              loading={detailLoading}
              errorMessage={detailError}
              onRetry={detailRetryAction ? () => void handleAction(detailRetryAction) : null}
              onOpenChange={setDetailOpen}
              onAction={handleAction}
            />
          </aside>
        ) : (
          <DesktopPreviewSidebar onOpenCustomer={() => void openDefaultCustomerPreview()} />
        ) : null}
      </div>

      {!isDesktop ? (
        <DetailPanel
          detail={detail}
          open={detailOpen}
          loading={detailLoading}
          errorMessage={detailError}
          onRetry={detailRetryAction ? () => void handleAction(detailRetryAction) : null}
          onOpenChange={setDetailOpen}
          onAction={handleAction}
        />
      ) : null}
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<WorkbenchPage />} />
      <Route path="/explain" element={<ExplainPage />} />
    </Routes>
  )
}
