import type { ComponentType } from 'react'

import type { UIAction, UIComponent } from '@/lib/protocol'
import { ProtocolRenderer } from '@/components/protocol-renderer'

export type RendererProps = {
  component: UIComponent
  onAction: (action: UIAction) => void
}

export const rendererRegistry: Record<string, ComponentType<RendererProps>> = {
  customer_spotlight: ProtocolRenderer,
  customer_overview: ProtocolRenderer,
  relationship_plan: ProtocolRenderer,
  knowledge_briefs: ProtocolRenderer,
  workflow_checkpoint: ProtocolRenderer,
  customer_list: ProtocolRenderer,
  category_overview: ProtocolRenderer,
  product_grid: ProtocolRenderer,
  task_list: ProtocolRenderer,
  message_draft: ProtocolRenderer,
  memory_briefs: ProtocolRenderer,
  memory_suggestions: ProtocolRenderer,
  session_checkpoint_list: ProtocolRenderer,
  trace_timeline: ProtocolRenderer,
  safety_notice: ProtocolRenderer,
  clarification_notice: ProtocolRenderer,
  action_result_notice: ProtocolRenderer,
  detail_kv: ProtocolRenderer,
  tag_group: ProtocolRenderer,
  timeline: ProtocolRenderer,
  image_panel: ProtocolRenderer,
}

export function resolveRenderer(componentType: string): ComponentType<RendererProps> {
  return rendererRegistry[componentType] ?? ProtocolRenderer
}
