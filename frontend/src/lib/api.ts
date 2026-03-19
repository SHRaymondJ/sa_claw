import type {
  BootstrapResponse,
  ChatResponse,
  DetailResponse,
  ExplainResponse,
  TaskCompleteResponse,
} from '@/lib/protocol'

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }

  return (await response.json()) as T
}

export function getBootstrap() {
  return requestJson<BootstrapResponse>('/api/crm/bootstrap')
}

export function sendChat(message: string, sessionId?: string | null) {
  return requestJson<ChatResponse>('/api/crm/chat/send', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId ?? undefined }),
  })
}

export function getCustomerDetail(customerId: string) {
  return requestJson<DetailResponse>(`/api/crm/customers/${customerId}`)
}

export function getProductDetail(productId: string) {
  return requestJson<DetailResponse>(`/api/crm/products/${productId}`)
}

export function getTaskDetail(taskId: string) {
  return requestJson<DetailResponse>(`/api/crm/tasks/${taskId}`)
}

export function completeTask(taskId: string) {
  return requestJson<TaskCompleteResponse>(`/api/crm/tasks/${taskId}/complete`, {
    method: 'POST',
  })
}

export function getExplain() {
  return requestJson<ExplainResponse>('/api/crm/explain')
}
