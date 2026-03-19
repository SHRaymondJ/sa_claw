import { completeTask, getCustomerDetail, getProductDetail, getTaskDetail } from '@/lib/api'
import type { DetailResponse, TaskCompleteResponse, UIAction } from '@/lib/protocol'

type ActionContext = {
  setDetail: (detail: DetailResponse | null) => void
  setDetailOpen: (open: boolean) => void
  appendTaskCompletion: (payload: TaskCompleteResponse) => void
}

type ActionHandler = (action: UIAction, context: ActionContext) => Promise<void>

const handlers: Record<string, ActionHandler> = {
  async open_customer(action, context) {
    if (!action.entity_id) return
    const payload = await getCustomerDetail(action.entity_id)
    context.setDetail(payload)
    context.setDetailOpen(true)
  },
  async open_product(action, context) {
    if (!action.entity_id) return
    const payload = await getProductDetail(action.entity_id)
    context.setDetail(payload)
    context.setDetailOpen(true)
  },
  async open_task(action, context) {
    if (!action.entity_id) return
    const payload = await getTaskDetail(action.entity_id)
    context.setDetail(payload)
    context.setDetailOpen(true)
  },
  async complete_task(action, context) {
    if (!action.entity_id) return
    const payload = await completeTask(action.entity_id)
    context.appendTaskCompletion(payload)
  },
}

export async function dispatchAction(action: UIAction, context: ActionContext): Promise<void> {
  const handler = handlers[action.action_type]
  if (!handler) {
    return
  }

  await handler(action, context)
}
