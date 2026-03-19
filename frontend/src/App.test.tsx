import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/react'

import App from '@/App'
import { getBootstrap, sendChat } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  getBootstrap: vi.fn().mockResolvedValue({
    advisor_name: '林顾问',
    store_name: '上海静安店',
    brand_name: '缦序',
    pending_task_count: 7,
    quick_prompts: ['帮我找重点客户'],
  }),
  sendChat: vi.fn(),
  getCustomerDetail: vi.fn(),
  getProductDetail: vi.fn(),
  getTaskDetail: vi.fn(),
  completeTask: vi.fn(),
  getExplain: vi.fn().mockResolvedValue({
    title: '说明',
    sections: [],
  }),
}))

describe('App', () => {
  it('shows editorial loading shell before bootstrap resolves', async () => {
    let resolveBootstrap: undefined | ((value: {
      advisor_name: string
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
        advisor_name: '林顾问',
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
    expect(screen.getByText('帮我找重点客户')).toBeInTheDocument()
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
      }>
      ui_schema: []
      supported_actions: string[]
      safety_status: 'allowed'
      context_version: string
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
    await user.type(screen.getByPlaceholderText('例如：帮我找今天该优先跟进但还没联系的高净值客户'), '帮我找重点客户')
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
          },
        ],
        ui_schema: [],
        supported_actions: [],
        safety_status: 'allowed',
        context_version: 'crm-v1',
      })
    }

    await waitFor(() => {
      expect(screen.getByText('已经整理好 3 位建议优先联系的客户。')).toBeInTheDocument()
    })
  })
})
