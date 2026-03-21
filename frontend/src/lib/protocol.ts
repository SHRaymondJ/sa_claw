export type ActionVariant = 'primary' | 'secondary' | 'ghost'

export type UIAction = {
  action_type: string
  label: string
  entity_type: string
  entity_id?: string | null
  method: 'GET' | 'POST'
  variant: ActionVariant
  payload: Record<string, unknown>
}

export type UIComponent = {
  component_type: string
  component_id: string
  title: string
  props: Record<string, unknown>
  actions: UIAction[]
}

export type ChatMessage = {
  message_id: string
  role: 'user' | 'assistant' | 'system'
  text: string
  created_at: string
  ui_schema: UIComponent[]
  meta?: Record<string, unknown>
}

export type ChatResponse = {
  session_id: string
  messages: ChatMessage[]
  ui_schema: UIComponent[]
  supported_actions: string[]
  safety_status: 'allowed' | 'rejected'
  context_version: string
  meta?: Record<string, unknown>
  clarification_needed?: boolean
}

export type BootstrapResponse = {
  advisor_id: string
  advisor_name: string
  store_id: string
  store_name: string
  brand_name: string
  pending_task_count: number
  quick_prompts: string[]
  preview_customer_id?: string | null
}

export type ExplainSection = {
  key: string
  title: string
  summary: string
  points: string[]
  steps: string[]
  tags: string[]
}

export type ExplainResponse = {
  title: string
  subtitle: string
  sections: ExplainSection[]
  maintenance_checklist: string[]
  blockers: string[]
  protocol_example: Record<string, unknown>
}

export type DetailResponse = {
  entity_type: 'customer' | 'product' | 'task' | 'session'
  entity_id: string
  title: string
  subtitle: string
  summary: string
  ui_schema: UIComponent[]
}

export type TaskCompleteResponse = {
  task_id: string
  status: string
  message: string
  updated_component: UIComponent
  session_meta?: Record<string, unknown>
}

export type ActionMutationResponse = {
  entity_id: string
  status: string
  message: string
  session_meta?: Record<string, unknown>
  updated_component?: UIComponent | null
}
