import { MemoryRouter } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'

import App from '@/App'

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
})
