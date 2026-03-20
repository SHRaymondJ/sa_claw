import { render, screen } from '@testing-library/react'

import { ProtocolRenderer } from '@/components/protocol-renderer'

describe('ProtocolRenderer', () => {
  it('renders product match reasons and display tags', () => {
    render(
      <ProtocolRenderer
        component={{
          component_type: 'product_grid',
          component_id: 'product-grid-1',
          title: '夏天可优先推荐的门店单品',
          props: {
            items: [
              {
                id: 'P001',
                name: '静线 象牙白双排扣外套',
                price: 1299,
                category: '西装',
                color: '象牙白',
                availability: '现货充足',
                image_url: '/crm/products/look-01.svg',
                match_reason: '属于 春夏城市系列，适合 夏天 场景；门店现货 6 件',
                display_tags: ['夏天', '可通勤', '象牙白'],
              },
            ],
          },
          actions: [],
        }}
        onAction={() => {}}
      />,
    )

    expect(screen.getByText('属于 春夏城市系列，适合 夏天 场景；门店现货 6 件')).toBeInTheDocument()
    expect(screen.getByText('夏天')).toBeInTheDocument()
    expect(screen.getByText('可通勤')).toBeInTheDocument()
  })

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
