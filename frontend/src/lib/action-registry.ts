import {
  approveMemorySuggestion,
  completeTask,
  getCustomerDetail,
  getProductDetail,
  getSessionDetail,
  getTaskDetail,
  rejectMemorySuggestion,
} from '@/lib/api'
import type { ActionMutationResponse, DetailResponse, TaskCompleteResponse, UIAction } from '@/lib/protocol'

type ActionContext = {
  setDetail: (detail: DetailResponse | null) => void
  setDetailOpen: (open: boolean) => void
  setDetailLoading?: (loading: boolean) => void
  setDetailError?: (message: string | null) => void
  setDetailRetryAction?: (action: UIAction | null) => void
  setSessionMeta?: (meta: Record<string, unknown> | null) => void
  appendTaskCompletion: (payload: TaskCompleteResponse) => void
  appendMutationNotice?: (payload: ActionMutationResponse) => void
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
    context.setDetailError?.(null)
    context.setDetailRetryAction?.(action)
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
    context.setDetailError?.(null)
    context.setDetailRetryAction?.(action)
    try {
      const payload = await withMinimumDelay(getProductDetail(action.entity_id))
      context.setDetail(payload)
    } finally {
      context.setDetailLoading?.(false)
    }
  },
  async open_session(action, context) {
    if (!action.entity_id) return
    context.setDetailOpen(true)
    context.setDetailLoading?.(true)
    context.setDetailError?.(null)
    context.setDetailRetryAction?.(action)
    try {
      const payload = await withMinimumDelay(getSessionDetail(action.entity_id))
      context.setDetail(payload)
    } finally {
      context.setDetailLoading?.(false)
    }
  },
  async open_task(action, context) {
    if (!action.entity_id) return
    context.setDetailOpen(true)
    context.setDetailLoading?.(true)
    context.setDetailError?.(null)
    context.setDetailRetryAction?.(action)
    try {
      const payload = await withMinimumDelay(getTaskDetail(action.entity_id))
      context.setDetail(payload)
    } finally {
      context.setDetailLoading?.(false)
    }
  },
  async complete_task(action, context) {
    if (!action.entity_id) return
    const shouldProceed = window.confirm('确认将这条任务标记为已完成吗？完成后会同步更新当前会话。')
    if (!shouldProceed) {
      return
    }
    const payload = await completeTask(action.entity_id)
    context.appendTaskCompletion(payload)
    context.setSessionMeta?.((payload.session_meta as Record<string, unknown>) ?? null)
  },
  async approve_memory_suggestion(action, context) {
    const suggestionId = String(action.entity_id ?? action.payload.suggestion_id ?? '')
    const customerId = String(action.payload.customer_id ?? '')
    if (!suggestionId || !customerId) return
    const payload = await approveMemorySuggestion(suggestionId)
    context.appendMutationNotice?.(payload)
    context.setSessionMeta?.((payload.session_meta as Record<string, unknown>) ?? null)
    context.setDetailOpen(true)
    context.setDetailLoading?.(true)
    context.setDetailError?.(null)
    context.setDetailRetryAction?.({
      action_type: 'open_customer',
      label: '重试查看客户详情',
      entity_type: 'customer',
      entity_id: customerId,
      method: 'GET',
      variant: 'secondary',
      payload: {},
    })
    try {
      const detailPayload = await withMinimumDelay(getCustomerDetail(customerId))
      context.setDetail(detailPayload)
    } catch (error) {
      const message = error instanceof Error ? error.message : '客户详情刷新失败'
      context.setDetailError?.(`记录已更新，但客户详情刷新失败：${message}`)
    } finally {
      context.setDetailLoading?.(false)
    }
  },
  async reject_memory_suggestion(action, context) {
    const suggestionId = String(action.entity_id ?? action.payload.suggestion_id ?? '')
    const customerId = String(action.payload.customer_id ?? '')
    if (!suggestionId || !customerId) return
    const payload = await rejectMemorySuggestion(suggestionId)
    context.appendMutationNotice?.(payload)
    context.setSessionMeta?.((payload.session_meta as Record<string, unknown>) ?? null)
    context.setDetailOpen(true)
    context.setDetailLoading?.(true)
    context.setDetailError?.(null)
    context.setDetailRetryAction?.({
      action_type: 'open_customer',
      label: '重试查看客户详情',
      entity_type: 'customer',
      entity_id: customerId,
      method: 'GET',
      variant: 'secondary',
      payload: {},
    })
    try {
      const detailPayload = await withMinimumDelay(getCustomerDetail(customerId))
      context.setDetail(detailPayload)
    } catch (error) {
      const message = error instanceof Error ? error.message : '客户详情刷新失败'
      context.setDetailError?.(`记录已更新，但客户详情刷新失败：${message}`)
    } finally {
      context.setDetailLoading?.(false)
    }
  },
}

export async function dispatchAction(action: UIAction, context: ActionContext): Promise<void> {
  const handler = handlers[action.action_type]
  if (!handler) {
    return
  }

  await handler(action, context)
}
