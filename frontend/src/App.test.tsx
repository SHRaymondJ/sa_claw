import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/react'

import App from '@/App'
import { getBootstrap, getCustomerDetail, sendChat } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  APIError: class APIError extends Error {
    status: number

    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  },
  setRequestIdentity: vi.fn(),
  getBootstrap: vi.fn().mockResolvedValue({
    advisor_id: 'advisor-demo-001',
    advisor_name: '林顾问',
    store_id: 'store-sh-jingan',
    store_name: '上海静安店',
    brand_name: '缦序',
    pending_task_count: 7,
    quick_prompts: ['帮我找重点客户'],
    preview_customer_id: 'C001',
  }),
  sendChat: vi.fn(),
  getCustomerDetail: vi.fn().mockResolvedValue({
    entity_type: 'customer',
    entity_id: 'C001',
    title: '乔知夏',
    subtitle: '重点客户',
    summary: '客户详情',
    ui_schema: [],
  }),
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
      preview_customer_id?: string | null
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
          preview_customer_id: 'C001',
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
    expect(screen.getByText('帮我找重点客户')).toBeInTheDocument()
    expect(screen.queryByText(/推荐客户 3 人/)).not.toBeInTheDocument()
    expect(screen.queryByText(/林知夏/)).not.toBeInTheDocument()
    expect(screen.getByTestId('composer-shell')).toBeVisible()
  })

  it('renders empty-state quick prompts from bootstrap instead of fixed demo labels', async () => {
    vi.mocked(getBootstrap).mockResolvedValueOnce({
      advisor_id: 'advisor-demo-001',
      advisor_name: '林顾问',
      store_id: 'store-sh-jingan',
      store_name: '上海静安店',
      brand_name: '缦序',
      pending_task_count: 7,
      quick_prompts: ['帮我找重点客户', '看看通勤西装'],
      preview_customer_id: 'C001',
    })

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('帮我找重点客户')).toBeInTheDocument()
    })
    expect(screen.getByText('看看通勤西装')).toBeInTheDocument()
    expect(screen.queryByText('今天优先跟进客户')).not.toBeInTheDocument()
    expect(screen.queryByText('通勤西装现货')).not.toBeInTheDocument()
  })

  it('does not fabricate demo brand or advisor labels when bootstrap fields are missing', async () => {
    vi.mocked(getBootstrap).mockResolvedValueOnce({
      advisor_id: 'advisor-demo-001',
      advisor_name: '',
      store_id: 'store-sh-jingan',
      store_name: '',
      brand_name: '',
      pending_task_count: 0,
      quick_prompts: ['帮我找重点客户'],
      preview_customer_id: null,
    })

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('导购席位')).toBeInTheDocument()
    })
    expect(screen.queryByText('缦序 导购席位')).not.toBeInTheDocument()
    expect(screen.queryByText(/林顾问/)).not.toBeInTheDocument()
    expect(screen.getByText(/信息待同步/)).toBeInTheDocument()
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

  it('opens the bootstrap-provided preview customer instead of a fixed demo id', async () => {
    const user = userEvent.setup()
    vi.mocked(getBootstrap).mockResolvedValueOnce({
      advisor_id: 'advisor-demo-001',
      advisor_name: '林顾问',
      store_id: 'store-sh-jingan',
      store_name: '上海静安店',
      brand_name: '缦序',
      pending_task_count: 7,
      quick_prompts: ['帮我找重点客户'],
      preview_customer_id: 'C245',
    })
    vi.mocked(getCustomerDetail).mockResolvedValueOnce({
      entity_type: 'customer',
      entity_id: 'C245',
      title: '周若汐',
      subtitle: '高潜客户',
      summary: '客户详情',
      ui_schema: [],
    })

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await screen.findByText('缦序 导购席位')
    await user.click(screen.getByRole('button', { name: '查看推荐客户详情' }))

    await waitFor(() => {
      expect(getCustomerDetail).toHaveBeenCalledWith('C245')
    })
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

  it('shows a rate limit hint when chat send is throttled', async () => {
    const user = userEvent.setup()
    const { APIError } = await import('@/lib/api')
    vi.mocked(sendChat).mockRejectedValueOnce(new APIError(429, 'rate limit exceeded'))

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await screen.findByText('缦序 导购席位')
    await user.type(screen.getByRole('textbox'), '帮我找重点客户')
    await user.click(screen.getByRole('button', { name: '发送' }))

    await waitFor(() => {
      expect(screen.getByText(/当前发送过快/)).toBeInTheDocument()
    })
    expect(screen.getByText('请稍等片刻再继续发送，当前输入内容不会丢失。')).toBeInTheDocument()
  })
})
