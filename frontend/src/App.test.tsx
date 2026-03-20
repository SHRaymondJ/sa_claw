import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/react'

import App from '@/App'
import { getBootstrap, sendChat } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  APIError: class APIError extends Error {},
  setRequestIdentity: vi.fn(),
  getBootstrap: vi.fn().mockResolvedValue({
    advisor_id: 'advisor-demo-001',
    advisor_name: '林顾问',
    store_id: 'store-sh-jingan',
    store_name: '上海静安店',
    brand_name: '缦序',
    pending_task_count: 7,
    quick_prompts: ['帮我找重点客户'],
  }),
  sendChat: vi.fn(),
  getCustomerDetail: vi.fn(),
  getSessionDetail: vi.fn(),
  getProductDetail: vi.fn(),
  getTaskDetail: vi.fn(),
  completeTask: vi.fn(),
  approveMemorySuggestion: vi.fn(),
  rejectMemorySuggestion: vi.fn(),
  getExplain: vi.fn().mockResolvedValue({
    title: '说明',
    sections: [],
  }),
}))

describe('App', () => {
  it('shows editorial loading shell before bootstrap resolves', async () => {
    let resolveBootstrap: undefined | ((value: {
      advisor_id: string
      advisor_name: string
      store_id: string
      store_name: string
      brand_name: string
      pending_task_count: number
      quick_prompts: string[]
    }) => void)

    vi.mocked(getBootstrap).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveBootstrap = resolve
      }),
    )

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByText('正在整理今日待办与重点客户')).toBeInTheDocument()

    if (resolveBootstrap) {
        resolveBootstrap({
          advisor_id: 'advisor-demo-001',
          advisor_name: '林顾问',
          store_id: 'store-sh-jingan',
          store_name: '上海静安店',
          brand_name: '缦序',
          pending_task_count: 7,
        quick_prompts: ['帮我找重点客户'],
      })
    }

    await waitFor(() => {
      expect(screen.getByText('缦序 导购席位')).toBeInTheDocument()
    })
  })

  it('renders workbench bootstrap state', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('缦序 导购席位')).toBeInTheDocument()
    })
    expect(screen.getByText('今天优先跟进客户')).toBeInTheDocument()
    expect(screen.getByTestId('composer-shell')).toBeVisible()
  })

  it('shows a pending response shell while sending a message', async () => {
    const user = userEvent.setup()
    let resolveChat: undefined | ((value: {
      session_id: string
      messages: Array<{
        message_id: string
        role: 'assistant'
        text: string
        created_at: string
        ui_schema: []
        meta?: Record<string, unknown>
      }>
      ui_schema: []
      supported_actions: string[]
      safety_status: 'allowed'
      context_version: string
      meta?: Record<string, unknown>
    }) => void)

    vi.mocked(sendChat).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveChat = resolve
      }),
    )

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await screen.findByText('缦序 导购席位')
    await user.type(screen.getByRole('textbox'), '帮我找重点客户')
    await user.click(screen.getByRole('button', { name: '发送' }))

    expect(screen.getByText('正在整理本次客户建议')).toBeInTheDocument()

    if (resolveChat) {
      resolveChat({
        session_id: 'session-1',
        messages: [
          {
            message_id: 'assistant-1',
            role: 'assistant',
            text: '已经整理好 3 位建议优先联系的客户。',
            created_at: new Date().toISOString(),
            ui_schema: [],
            meta: {
              status_hint: '筛优先客户',
              handoff_reason: '本轮首次进入当前工作流。',
            },
          },
        ],
        ui_schema: [],
        supported_actions: [],
        safety_status: 'allowed',
        context_version: 'crm-v1',
        meta: {
          conversation_mode_label: '筛优先客户',
          session_snapshot: {
            active_customer_name: '未锁定',
            active_intent: 'customer_filter',
            last_response_shape: 'workflow_checkpoint+customer_list',
            handoff_reason: '本轮首次进入当前工作流。',
          },
        },
      })
    }

    await waitFor(() => {
      expect(screen.getByText('已经整理好 3 位建议优先联系的客户。')).toBeInTheDocument()
    })
    expect(screen.getByText('当前任务类型')).toBeInTheDocument()
    expect(screen.getAllByText('筛优先客户').length).toBeGreaterThan(0)
    expect(screen.getByText(/本轮切换原因/)).toBeInTheDocument()
  })

  it('shows retry notice when sending fails', async () => {
    const user = userEvent.setup()
    vi.mocked(sendChat).mockRejectedValueOnce(new Error('service unavailable'))

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await screen.findByText('缦序 导购席位')
    await user.type(screen.getByRole('textbox'), '帮我找重点客户')
    await user.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => {
      expect(screen.getAllByText('发送失败').length).toBeGreaterThan(0)
    })
    expect(screen.getByRole('button', { name: '重试发送' })).toBeInTheDocument()
  })
})
