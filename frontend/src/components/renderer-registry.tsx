import type { ComponentType } from 'react'

import type { UIAction, UIComponent } from '@/lib/protocol'
import { ProtocolRenderer } from '@/components/protocol-renderer'

export type RendererProps = {
  component: UIComponent
  onAction: (action: UIAction) => void
}

export const rendererRegistry: Record<string, ComponentType<RendererProps>> = {
  customer_list: ProtocolRenderer,
  product_grid: ProtocolRenderer,
  task_list: ProtocolRenderer,
  message_draft: ProtocolRenderer,
  trace_timeline: ProtocolRenderer,
  safety_notice: ProtocolRenderer,
  detail_kv: ProtocolRenderer,
  tag_group: ProtocolRenderer,
  timeline: ProtocolRenderer,
  image_panel: ProtocolRenderer,
}

export function resolveRenderer(componentType: string): ComponentType<RendererProps> {
  return rendererRegistry[componentType] ?? ProtocolRenderer
}
