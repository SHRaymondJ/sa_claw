import type {
  ActionMutationResponse,
  BootstrapResponse,
  ChatResponse,
  DetailResponse,
  ExplainResponse,
  TaskCompleteResponse,
} from '@/lib/protocol'

type RequestIdentity = {
  advisorId: string
  storeId: string
}

export class APIError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'APIError'
    this.status = status
  }
}

let currentIdentity: RequestIdentity | null = null

export function setRequestIdentity(identity: RequestIdentity | null) {
  currentIdentity = identity
}

function buildIdentityHeaders() {
  if (!currentIdentity?.advisorId || !currentIdentity?.storeId) {
    return {}
  }
  return {
    'X-Advisor-Id': currentIdentity.advisorId,
    'X-Store-Id': currentIdentity.storeId,
  }
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')
  for (const [key, value] of Object.entries(buildIdentityHeaders())) {
    headers.set(key, value)
  }

  const response = await fetch(url, {
    headers,
    ...init,
  })

  if (!response.ok) {
    let detail = ''
    try {
      const payload = (await response.json()) as { detail?: string }
      detail = payload.detail ?? ''
    } catch {
      detail = ''
    }
    throw new APIError(response.status, detail || `Request failed: ${response.status}`)
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

export function getSessionDetail(sessionId: string) {
  return requestJson<DetailResponse>(`/api/crm/sessions/${sessionId}`)
}

export function getTaskDetail(taskId: string) {
  return requestJson<DetailResponse>(`/api/crm/tasks/${taskId}`)
}

export function completeTask(taskId: string) {
  return requestJson<TaskCompleteResponse>(`/api/crm/tasks/${taskId}/complete`, {
    method: 'POST',
  })
}

export function approveMemorySuggestion(suggestionId: string) {
  return requestJson<ActionMutationResponse>(`/api/crm/memory-suggestions/${suggestionId}/approve`, {
    method: 'POST',
  })
}

export function rejectMemorySuggestion(suggestionId: string) {
  return requestJson<ActionMutationResponse>(`/api/crm/memory-suggestions/${suggestionId}/reject`, {
    method: 'POST',
  })
}

export function getExplain() {
  return requestJson<ExplainResponse>('/api/crm/explain')
}
