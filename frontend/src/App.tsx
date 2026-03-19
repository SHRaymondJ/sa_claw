import { useEffect, useMemo, useState } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import { BotMessageSquare, Database, GitBranch, LoaderCircle, SendHorizontal, ShieldCheck, Workflow } from 'lucide-react'

import { getBootstrap, getExplain, sendChat } from '@/lib/api'
import { DetailPanel } from '@/components/detail-panel'
import { resolveRenderer } from '@/components/renderer-registry'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import { dispatchAction } from '@/lib/action-registry'
import type { BootstrapResponse, ChatMessage, DetailResponse, ExplainResponse, TaskCompleteResponse, UIAction } from '@/lib/protocol'
import { cn } from '@/lib/utils'
import { useMediaQuery } from '@/hooks/use-media-query'

function MessageBubble({ message, onAction }: { message: ChatMessage; onAction: (action: UIAction) => void }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser ? (
        <Avatar className="mt-1 hidden md:flex">
          <AvatarFallback>导</AvatarFallback>
        </Avatar>
      ) : null}
      <div className={cn('max-w-[86%] space-y-3 md:max-w-[72%]', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'border px-4 py-3 text-sm leading-7',
            isUser
              ? 'border-[var(--ink)] bg-[var(--ink)] text-[var(--paper)]'
              : 'border-[var(--line)] bg-[var(--paper)] text-[var(--ink)]',
          )}
        >
          {message.text}
        </div>
        {message.ui_schema.map((component) => (
          <MessageRenderer key={component.component_id} component={component} onAction={onAction} />
        ))}
      </div>
    </div>
  )
}

function MessageRenderer({ component, onAction }: { component: ChatMessage['ui_schema'][number]; onAction: (action: UIAction) => void }) {
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
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center justify-between gap-4 border border-[var(--line)] bg-[var(--paper)] px-5 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">解释页</p>
            <h1 className="mt-2 text-2xl font-semibold text-[var(--ink)]">{payload?.title ?? '加载中'}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">{payload?.subtitle}</p>
          </div>
          <Button asChild>
            <Link to="/">返回工作台</Link>
          </Button>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader>
              <Workflow className="h-5 w-5 text-[var(--muted)]" />
              <CardTitle>协议驱动</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-[var(--muted)]">
              后端负责返回协议，前端负责渲染与动作绑定。
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <Database className="h-5 w-5 text-[var(--muted)]" />
              <CardTitle>实体后链路</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-[var(--muted)]">
              卡片点击后进入客户、商品、任务详情与动作接口。
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <ShieldCheck className="h-5 w-5 text-[var(--muted)]" />
              <CardTitle>边界保护</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-[var(--muted)]">
              越界话题先拒答，不进入检索和生成。
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <GitBranch className="h-5 w-5 text-[var(--muted)]" />
              <CardTitle>维护可持续</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-[var(--muted)]">
              页面、组件、协议三层分别治理，不混在一起改。
            </CardContent>
          </Card>
        </div>
        <div className="grid gap-4">
          {payload?.sections.map((section) => (
            <Card key={section.key}>
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
                    <div key={point} className="border border-[var(--line)] bg-[var(--surface)] px-4 py-3 text-sm leading-6 text-[var(--ink)]">
                      {point}
                    </div>
                  ))}
                </div>
                <div className="space-y-3 border border-[var(--line)] bg-[var(--paper)] p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">落地流程</p>
                  {section.steps.map((step, index) => (
                    <div key={step} className="flex gap-3 text-sm leading-6 text-[var(--ink)]">
                      <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center border border-[var(--line)] bg-[var(--surface)] text-xs">
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
          <Card>
            <CardHeader>
              <CardTitle>协议示例</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto border border-[var(--line)] bg-[var(--surface)] p-4 text-xs leading-6 text-[var(--ink)]">
                {JSON.stringify(payload?.protocol_example ?? {}, null, 2)}
              </pre>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>维护清单</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {payload?.maintenance_checklist.map((item) => (
                <div key={item} className="border border-[var(--line)] bg-[var(--surface)] px-4 py-3 text-sm leading-6 text-[var(--ink)]">
                  {item}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
        <Card className="border-[var(--warning)] bg-[var(--warning-soft)]">
          <CardHeader>
            <CardTitle>当前外部阻塞</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {payload?.blockers.map((item) => (
              <div key={item} className="border border-[var(--line)] bg-[var(--paper)] px-4 py-3 text-sm leading-6 text-[var(--ink)]">
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
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      message_id: 'system-intro',
      role: 'assistant',
      text: '欢迎回来。你可以直接输入导购目标，我会基于客户、商品、库存和任务数据整理下一步建议。',
      created_at: new Date().toISOString(),
      ui_schema: [],
    },
  ])
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [detail, setDetail] = useState<DetailResponse | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const isDesktop = useMediaQuery('(min-width: 1024px)')

  useEffect(() => {
    void getBootstrap().then(setBootstrap)
  }, [])

  const statusText = useMemo(() => (loading ? '处理中' : '可继续提问'), [loading])

  function appendTaskCompletion(payload: TaskCompleteResponse) {
    setMessages((current) =>
      current.map((message) => ({
        ...message,
        ui_schema: message.ui_schema.map((component) => {
          if (component.component_type !== 'task_list') {
            return component
          }

          const items = (component.props.items as Array<Record<string, unknown>>).map((item) =>
            String(item.id) === payload.task_id
              ? { ...item, status: payload.status }
              : item,
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
  }

  async function handleSend(nextValue?: string) {
    const content = (nextValue ?? value).trim()
    if (!content || loading) {
      return
    }

    setLoading(true)
    try {
      const response = await sendChat(content, sessionId)
      setSessionId(response.session_id)
      setMessages((current) => [...current, ...response.messages])
      setValue('')
    } finally {
      setLoading(false)
    }
  }

  async function handleAction(action: UIAction) {
    await dispatchAction(action, {
      setDetail,
      setDetailOpen,
      appendTaskCompletion,
    })
  }

  return (
    <div className="min-h-screen bg-[var(--canvas)]">
      <div className="mx-auto flex min-h-screen max-w-[1440px] flex-col lg:grid lg:grid-cols-[minmax(0,1fr)_360px]">
        <main className="flex min-h-screen flex-col border-x border-[var(--line)] bg-[var(--paper)]">
          <header className="border-b border-[var(--line)] bg-[var(--surface)] px-4 py-4 md:px-6">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                  <BotMessageSquare className="h-4 w-4" />
                  门店工作台
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-xl font-semibold text-[var(--ink)]">
                    {bootstrap?.brand_name ?? '缦序'} 导购席位
                  </h1>
                  <Badge variant="accent">{statusText}</Badge>
                </div>
                <p className="text-sm text-[var(--muted)]">
                  {bootstrap?.advisor_name ?? '林顾问'} · {bootstrap?.store_name ?? '上海静安店'} · 今日待办{' '}
                  {bootstrap?.pending_task_count ?? '--'}
                </p>
              </div>
              <Button asChild variant="secondary" size="sm">
                <Link to="/explain">查看说明</Link>
              </Button>
            </div>
          </header>

          <div className="border-b border-[var(--line)] px-4 py-3 md:px-6">
            <div className="flex gap-2 overflow-x-auto">
              {bootstrap?.quick_prompts.map((prompt) => (
                <button
                  key={prompt}
                  className="shrink-0 border border-[var(--line)] bg-[var(--paper)] px-3 py-2 text-left text-xs leading-5 text-[var(--muted)] transition-colors hover:bg-[var(--surface)] md:text-sm"
                  onClick={() => void handleSend(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <ScrollArea className="min-h-0 flex-1">
            <div className="space-y-4 px-4 py-5 md:px-6">
              {messages.map((message) => (
                <MessageBubble key={message.message_id} message={message} onAction={handleAction} />
              ))}
            </div>
          </ScrollArea>

          <footer className="border-t border-[var(--line)] bg-[var(--paper)] px-4 py-4 md:px-6">
            <div className="space-y-3">
              <Textarea
                value={value}
                onChange={(event) => setValue(event.target.value)}
                placeholder="例如：帮我找今天该优先跟进但还没联系的高净值客户"
              />
              <div className="flex items-center justify-between gap-4">
                <p className="text-xs leading-5 text-[var(--muted)]">
                  当前为演示数据环境，客户、商品和任务均为脱敏虚构数据。
                </p>
                <Button variant="primary" onClick={() => void handleSend()} disabled={loading}>
                  {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
                  发送
                </Button>
              </div>
            </div>
          </footer>
        </main>

        {isDesktop ? (
          <aside className="hidden border-r border-[var(--line)] bg-[var(--canvas)] p-4 lg:block">
            <DetailPanel detail={detail} open={detailOpen} onOpenChange={setDetailOpen} onAction={handleAction} />
          </aside>
        ) : null}
      </div>

      {!isDesktop ? (
        <DetailPanel detail={detail} open={detailOpen} onOpenChange={setDetailOpen} onAction={handleAction} />
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
