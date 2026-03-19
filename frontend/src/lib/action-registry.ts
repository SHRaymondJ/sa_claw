import { completeTask, getCustomerDetail, getProductDetail, getTaskDetail } from '@/lib/api'
import type { DetailResponse, TaskCompleteResponse, UIAction } from '@/lib/protocol'

type ActionContext = {
  setDetail: (detail: DetailResponse | null) => void
  setDetailOpen: (open: boolean) => void
  setDetailLoading?: (loading: boolean) => void
  appendTaskCompletion: (payload: TaskCompleteResponse) => void
}

type ActionHandler = (action: UIAction, context: ActionContext) => Promise<void>

async function withMinimumDelay<T>(promise: Promise<T>, minimumMs = 260): Promise<T> {
  const startedAt = Date.now()
  const result = await promise
  const elapsed = Date.now() - startedAt
  if (elapsed < minimumMs) {
    await new Promise((resolve) => window.setTimeout(resolve, minimumMs - elapsed))
  }
  return result
}

const handlers: Record<string, ActionHandler> = {
  async open_customer(action, context) {
    if (!action.entity_id) return
    context.setDetailOpen(true)
    context.setDetailLoading?.(true)
    try {
      const payload = await withMinimumDelay(getCustomerDetail(action.entity_id))
      context.setDetail(payload)
    } finally {
      context.setDetailLoading?.(false)
    }
  },
  async open_product(action, context) {
    if (!action.entity_id) return
    context.setDetailOpen(true)
    context.setDetailLoading?.(true)
    try {
      const payload = await withMinimumDelay(getProductDetail(action.entity_id))
      context.setDetail(payload)
    } finally {
      context.setDetailLoading?.(false)
    }
  },
  async open_task(action, context) {
    if (!action.entity_id) return
    context.setDetailOpen(true)
    context.setDetailLoading?.(true)
    try {
      const payload = await withMinimumDelay(getTaskDetail(action.entity_id))
      context.setDetail(payload)
    } finally {
      context.setDetailLoading?.(false)
    }
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
