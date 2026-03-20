import { dispatchAction } from '@/lib/action-registry'
import { getCustomerDetail, getSessionDetail } from '@/lib/api'
import type { DetailResponse } from '@/lib/protocol'

vi.mock('@/lib/api', () => ({
  getCustomerDetail: vi.fn().mockResolvedValue({ entity_id: 'C001' }),
  getSessionDetail: vi.fn().mockResolvedValue({ entity_id: 's_1' }),
  getProductDetail: vi.fn().mockResolvedValue({ entity_id: 'P001' }),
  getTaskDetail: vi.fn().mockResolvedValue({ entity_id: 'T001' }),
  completeTask: vi.fn().mockResolvedValue({
    task_id: 'T001',
    status: 'done',
    message: 'ok',
    updated_component: {
      component_type: 'action_result_notice',
      component_id: 'task-card',
      title: '任务状态已更新',
      props: { message: 'ok', status: 'success' },
      actions: [],
    },
    session_meta: { session_id: 's_1', state_version: 2 },
  }),
  approveMemorySuggestion: vi.fn().mockResolvedValue({
    entity_id: '1',
    status: 'approved',
    message: 'ok',
    updated_component: {
      component_type: 'action_result_notice',
      component_id: 'notice-1',
      title: '客户记录已确认',
      props: { message: 'ok', status: 'success' },
      actions: [],
    },
  }),
  rejectMemorySuggestion: vi.fn().mockResolvedValue({ entity_id: '1', status: 'rejected', message: 'ok' }),
}))

describe('dispatchAction', () => {
  beforeEach(() => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

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
        setDetailError: vi.fn(),
        setDetailRetryAction: vi.fn(),
        setSessionMeta: vi.fn(),
        appendMutationNotice: vi.fn(),
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
        setDetailError: vi.fn(),
        setDetailRetryAction: vi.fn(),
        setSessionMeta: vi.fn(),
        appendMutationNotice: vi.fn(),
      },
    )

    expect(appendTaskCompletion).toHaveBeenCalled()
  })

  it('opens session detail through session action', async () => {
    const setDetail = vi.fn()

    await dispatchAction(
      {
        action_type: 'open_session',
        label: '查看会话节点',
        entity_type: 'session',
        entity_id: 's_1',
        method: 'GET',
        variant: 'secondary',
        payload: {},
      },
      {
        setDetail,
        setDetailOpen: vi.fn(),
        appendTaskCompletion: vi.fn(),
        setDetailError: vi.fn(),
        setDetailRetryAction: vi.fn(),
        setSessionMeta: vi.fn(),
        appendMutationNotice: vi.fn(),
      },
    )

    expect(getSessionDetail).toHaveBeenCalledWith('s_1')
    expect(setDetail).toHaveBeenCalled()
  })
})
