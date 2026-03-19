import { dispatchAction } from '@/lib/action-registry'

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
