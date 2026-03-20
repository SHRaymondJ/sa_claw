import { startTransition, useEffect, useMemo, useRef, useState } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import {
  BotMessageSquare,
  Database,
  GitBranch,
  LoaderCircle,
  SendHorizontal,
  ShieldCheck,
  Sparkles,
  Workflow,
} from 'lucide-react'

import { getBootstrap, getExplain, sendChat } from '@/lib/api'
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
  text: '欢迎回来。直接输入导购目标，工作台会结合客户、商品、库存和任务，整理可直接执行的建议。',
  created_at: new Date().toISOString(),
  ui_schema: [],
}

const MIN_RESPONSE_DELAY_MS = 520

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
    <div className="thread-enter max-w-[90%] space-y-3 md:max-w-[74%]">
      <div className="message-card shimmer-panel space-y-4 p-4 md:p-5">
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
      <div className="grid gap-3 md:grid-cols-2">
        <div className="soft-panel shimmer-panel p-4">
          <div className="skeleton-line h-3 w-16" />
          <div className="mt-4 skeleton-block h-24" />
        </div>
        <div className="soft-panel shimmer-panel p-4">
          <div className="skeleton-line h-3 w-20" />
          <div className="mt-4 skeleton-block h-24" />
        </div>
      </div>
    </div>
  )
}

function MobileQuickPromptRail({
  prompts,
  onSelect,
}: {
  prompts: string[]
  onSelect: (prompt: string) => void
}) {
  return (
    <div className="thread-enter space-y-2">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">
        <Sparkles className="h-3.5 w-3.5" />
        直接开始
      </div>
      <div className="grid grid-cols-2 gap-2">
        {prompts.map((prompt) => (
          <button key={prompt} className="mobile-prompt-chip" onClick={() => onSelect(prompt)}>
            {prompt}
          </button>
        ))}
      </div>
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

  return (
    <div className={cn('thread-enter flex gap-3', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser ? (
        <Avatar className="mt-1 hidden border border-[var(--line)] bg-[var(--surface)] md:flex">
          <AvatarFallback>导</AvatarFallback>
        </Avatar>
      ) : null}
      <div className={cn('max-w-[90%] space-y-3 md:max-w-[74%]', isUser ? 'items-end' : 'items-start')}>
        <div className={cn('message-card p-4 md:p-5', isUser ? 'message-card-user' : 'message-card-assistant')}>
          <div className="flex items-center justify-between gap-3">
            <div className="text-[11px] uppercase tracking-[0.22em] text-[var(--muted)]">
              {isUser ? '本次输入' : '导购建议'}
            </div>
            <div className={cn('text-[11px]', isUser ? 'text-white/72' : 'text-[var(--muted)]')}>{formatTime(message.created_at)}</div>
          </div>
          <p className={cn('mt-3 text-sm leading-7 md:text-[15px]', isUser ? 'text-[var(--paper)]' : 'text-[var(--ink)]')}>{message.text}</p>
        </div>
        {message.ui_schema.map((component) => (
          <MessageRenderer key={component.component_id} component={component} onAction={onAction} />
        ))}
      </div>
    </div>
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
  const [detail, setDetail] = useState<DetailResponse | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const messageViewportRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let cancelled = false

    void withMinimumDelay(getBootstrap(), 360)
      .then((payload) => {
        if (cancelled) return
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

  const statusText = useMemo(() => (loading ? '处理中' : '可继续提问'), [loading])

  useEffect(() => {
    const viewport = messageViewportRef.current
    if (!viewport) {
      return
    }

    const frame = window.requestAnimationFrame(() => {
      if (typeof viewport.scrollTo === 'function') {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: 'smooth',
        })
        return
      }

      viewport.scrollTop = viewport.scrollHeight
    })

    return () => window.cancelAnimationFrame(frame)
  }, [messages, loading])

  function appendTaskCompletion(payload: TaskCompleteResponse) {
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
      startTransition(() => {
        setMessages((current) => [...current, ...response.messages])
      })
    } finally {
      setLoading(false)
    }
  }

  async function handleAction(action: UIAction) {
    setDetail(null)
    await dispatchAction(action, {
      setDetail,
      setDetailOpen,
      setDetailLoading,
      appendTaskCompletion,
    })
  }

  if (bootstrapLoading) {
    return <BootstrapShell />
  }

  const compactMeta = `${bootstrap?.advisor_name ?? '林顾问'} · ${bootstrap?.store_name ?? '上海静安店'}`

  return (
    <div className="min-h-[100dvh] bg-[var(--canvas)]">
      <div className="mx-auto flex min-h-[100dvh] max-w-[1480px] flex-col px-0 lg:grid lg:min-h-screen lg:grid-cols-[minmax(0,1fr)_368px] lg:gap-5 lg:px-5 lg:py-5">
        <main className="relative flex h-[100dvh] min-h-[100dvh] flex-col overflow-hidden border-x border-[var(--line)] bg-[var(--paper)] lg:h-[calc(100vh-2.5rem)] lg:min-h-0 lg:border lg:shadow-[var(--shadow-soft)]">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-56 bg-[radial-gradient(circle_at_top,rgba(196,180,154,0.32),transparent_62%)]" />

          <header className="relative border-b border-[var(--line)] bg-[linear-gradient(180deg,rgba(250,248,243,0.96),rgba(244,240,231,0.9))] px-4 py-2.5 backdrop-blur-sm md:px-6 md:py-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 space-y-2 md:space-y-4">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-[var(--muted)]">
                  <BotMessageSquare className="h-4 w-4" />
                  门店工作台
                </div>
                <div className="flex flex-wrap items-center gap-2 md:gap-3">
                  <h1 className="font-serif-display text-[22px] leading-none text-[var(--ink)] md:text-[36px]">
                    {bootstrap?.brand_name ?? '缦序'} 导购席位
                  </h1>
                  <Badge variant={loading ? 'accent' : 'dark'}>{statusText}</Badge>
                </div>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs leading-5 text-[var(--muted)] md:text-sm md:leading-6">
                  <span>{compactMeta}</span>
                  <span>今日待办 {bootstrap?.pending_task_count ?? '--'}</span>
                  {!isDesktop ? <span>{loading ? '正在整理本轮建议' : '可直接继续提问'}</span> : null}
                </div>
              </div>
              <Button asChild variant="secondary" size="sm" className="self-start px-2.5 text-xs md:px-3">
                <Link to="/explain">{isDesktop ? '查看说明' : '说明'}</Link>
              </Button>
            </div>

            {isDesktop ? (
              <div className="mt-5 grid gap-3 md:grid-cols-3">
                <div className="hero-stat-card">
                  <p className="hero-stat-label">今日重点</p>
                  <p className="hero-stat-value">{bootstrap?.pending_task_count ?? '--'} 条</p>
                  <p className="hero-stat-copy">优先处理高净值客户回访与试穿邀约。</p>
                </div>
                <div className="hero-stat-card">
                  <p className="hero-stat-label">最近主题</p>
                  <p className="hero-stat-value">通勤西装</p>
                  <p className="hero-stat-copy">本周查询集中在轻羊毛、浅灰与米白色系。</p>
                </div>
                <div className="hero-stat-card">
                  <p className="hero-stat-label">当前节奏</p>
                  <p className="hero-stat-value">{loading ? '整理中' : '可执行'}</p>
                  <p className="hero-stat-copy">先给结果，再把客户、商品与动作稳定串起来。</p>
                </div>
              </div>
            ) : (
              <div className="mt-2 flex flex-wrap gap-2">
                <span className="mobile-summary-pill">待办 {bootstrap?.pending_task_count ?? '--'}</span>
                <span className="mobile-summary-pill">主题 通勤</span>
                <span className="mobile-summary-pill">{loading ? '整理中' : '在线'}</span>
              </div>
            )}
          </header>

          {isDesktop ? (
            <div className="border-b border-[var(--line)] bg-[var(--surface)]/75 px-4 py-2 md:px-6 md:py-3">
              <div className="flex gap-2 overflow-x-auto pb-1">
                {bootstrap?.quick_prompts.map((prompt, index) => (
                  <button
                    key={prompt}
                    className={cn('prompt-chip', index === 0 ? 'prompt-chip-active' : undefined)}
                    onClick={() => void handleSend(prompt)}
                  >
                    <span className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">快捷场景</span>
                    <span className="block text-[13px] leading-5 text-[var(--ink)] md:text-sm md:leading-6">{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="relative min-h-0 flex-1 overflow-hidden">
            <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-16 bg-[linear-gradient(180deg,rgba(251,248,242,0),rgba(251,248,242,0.94))]" />
            <div
              ref={messageViewportRef}
              className="min-h-0 h-full overflow-y-auto overscroll-contain scroll-smooth"
            >
              <div className="space-y-4 px-4 py-5 pb-8 md:px-6 md:pb-10">
                {messages.map((message) => (
                  <MessageBubble key={message.message_id} message={message} onAction={handleAction} />
                ))}
                {!isDesktop && messages.length === 1 && !loading ? (
                  <MobileQuickPromptRail prompts={bootstrap?.quick_prompts ?? []} onSelect={(prompt) => void handleSend(prompt)} />
                ) : null}
                {loading ? <PendingReplyCard /> : null}
              </div>
            </div>
          </div>

          <footer
            data-testid="composer-shell"
            className="z-20 shrink-0 border-t border-[var(--line)] bg-[linear-gradient(180deg,rgba(250,248,243,0.88),rgba(252,251,247,0.98))] px-4 py-2 pb-[calc(env(safe-area-inset-bottom)+6px)] shadow-[0_-12px_28px_rgba(24,18,12,0.08)] backdrop-blur-xl md:px-6 md:py-4"
          >
            <div className="soft-panel border-[var(--line-strong)] bg-[linear-gradient(180deg,rgba(255,255,255,0.72),rgba(248,244,236,0.94))] p-2 md:p-4">
              <div className="space-y-1.5 md:space-y-3">
                {isDesktop ? (
                  <div className="flex items-center justify-between gap-3 border-b border-[var(--line)] pb-3">
                    <div>
                      <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--muted)]">本轮输入</p>
                      <p className="mt-1 text-sm text-[var(--muted)]">建议直接写目标、客户特征、商品范围或任务要求。</p>
                    </div>
                    {loading ? (
                      <div className="inline-flex items-center gap-2 text-xs text-[var(--muted)]">
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                        正在整理
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">发送导购目标</p>
                    {loading ? (
                      <div className="inline-flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
                        <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                        整理中
                      </div>
                    ) : null}
                  </div>
                )}
                <Textarea
                  value={value}
                  onChange={(event) => setValue(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey && !isDesktop) {
                      event.preventDefault()
                      void handleSend()
                    }
                  }}
                  className="min-h-[42px] max-h-[96px] resize-none border-0 bg-transparent px-0 py-0 text-[14px] leading-5 focus:border-0 focus-visible:ring-0 md:min-h-[104px] md:max-h-none md:text-[15px] md:leading-7"
                  placeholder="例如：帮我找今天该优先跟进但还没联系的高净值客户"
                />
                <div className="flex items-center justify-between gap-3 border-t border-[var(--line)] pt-2 md:gap-4 md:pt-3">
                  <p className="text-[10px] leading-4 text-[var(--muted)] md:text-xs md:leading-5">
                    {isDesktop
                      ? '当前为演示数据环境，客户、商品和任务均为脱敏虚构数据。'
                      : 'Enter 发送'}
                  </p>
                  <Button
                    variant="primary"
                    onClick={() => void handleSend()}
                    disabled={loading}
                    className="h-9 min-w-9 px-3 md:h-10 md:px-4"
                    aria-label="发送"
                  >
                    {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
                    {isDesktop ? '发送' : null}
                  </Button>
                </div>
              </div>
            </div>
          </footer>
        </main>

        {isDesktop ? (
          <aside className="hidden lg:block">
            <DetailPanel detail={detail} open={detailOpen} loading={detailLoading} onOpenChange={setDetailOpen} onAction={handleAction} />
          </aside>
        ) : null}
      </div>

      {!isDesktop ? (
        <DetailPanel detail={detail} open={detailOpen} loading={detailLoading} onOpenChange={setDetailOpen} onAction={handleAction} />
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
