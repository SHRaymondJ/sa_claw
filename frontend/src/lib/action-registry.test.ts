import { dispatchAction } from '@/lib/action-registry'
import { getCustomerDetail } from '@/lib/api'
import type { DetailResponse } from '@/lib/protocol'

vi.mock('@/lib/api', () => ({
  getCustomerDetail: vi.fn().mockResolvedValue({ entity_id: 'C001' }),
  getProductDetail: vi.fn().mockResolvedValue({ entity_id: 'P001' }),
  getTaskDetail: vi.fn().mockResolvedValue({ entity_id: 'T001' }),
  completeTask: vi.fn().mockResolvedValue({
    task_id: 'T001',
    status: 'done',
    message: 'ok',
    updated_component: {
      component_type: 'task_card',
      component_id: 'task-card',
      title: '任务',
      props: {},
      actions: [],
    },
  }),
}))

describe('dispatchAction', () => {
  it('shows loading feedback before customer detail is resolved', async () => {
    let resolveDetail: undefined | ((value: DetailResponse) => void)
    vi.mocked(getCustomerDetail).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveDetail = resolve
      }),
    )

    const setDetail = vi.fn()
    const setDetailOpen = vi.fn()
    const setDetailLoading = vi.fn()

    const pending = dispatchAction(
      {
        action_type: 'open_customer',
        label: '查看客户详情',
        entity_type: 'customer',
        entity_id: 'C001',
        method: 'GET',
        variant: 'secondary',
        payload: {},
      },
      {
        setDetail,
        setDetailOpen,
        appendTaskCompletion: vi.fn(),
        setDetailLoading,
      },
    )

    expect(setDetailOpen).toHaveBeenCalledWith(true)
    expect(setDetailLoading).toHaveBeenCalledWith(true)

    if (resolveDetail) {
      resolveDetail({
        entity_id: 'C001',
        entity_type: 'customer',
        title: '王曼青',
        subtitle: '黑金会员',
        summary: 'summary',
        ui_schema: [],
      })
    }
    await pending

    expect(setDetail).toHaveBeenCalledWith({
      entity_id: 'C001',
      entity_type: 'customer',
      title: '王曼青',
      subtitle: '黑金会员',
      summary: 'summary',
      ui_schema: [],
    })
    expect(setDetailLoading).toHaveBeenLastCalledWith(false)
  })

  it('dispatches known task completion action', async () => {
    const appendTaskCompletion = vi.fn()

    await dispatchAction(
      {
        action_type: 'complete_task',
        label: '完成任务',
        entity_type: 'task',
        entity_id: 'T001',
        method: 'POST',
        variant: 'primary',
        payload: {},
      },
      {
        setDetail: vi.fn(),
        setDetailOpen: vi.fn(),
        appendTaskCompletion,
      },
    )

    expect(appendTaskCompletion).toHaveBeenCalled()
  })
})
