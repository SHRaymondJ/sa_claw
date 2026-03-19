import { render, screen } from '@testing-library/react'

import { ProtocolRenderer } from '@/components/protocol-renderer'

describe('ProtocolRenderer', () => {
  it('renders fallback for unknown component types', () => {
    render(
      <ProtocolRenderer
        component={{
          component_type: 'unknown_block',
          component_id: 'unknown-1',
          title: '未知组件',
          props: {},
          actions: [],
        }}
        onAction={() => {}}
      />,
    )

    expect(screen.getByText('未注册组件')).toBeInTheDocument()
    expect(screen.getByText('unknown_block')).toBeInTheDocument()
  })
})
