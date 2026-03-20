import { render, screen } from '@testing-library/react'

import { ProtocolRenderer } from '@/components/protocol-renderer'

describe('ProtocolRenderer', () => {
  it('renders customer inventory overview with total and sample hint', () => {
    render(
      <ProtocolRenderer
        component={{
          component_type: 'customer_overview',
          component_id: 'customer-overview-1',
          title: '门店客户概览',
          props: {
            total_customers: 360,
            sample_limit: 6,
            tier_breakdown: [
              { tier: '高净值', count: 52 },
              { tier: '高潜', count: 118 },
            ],
          },
          actions: [],
        }}
        onAction={() => {}}
      />,
    )

    expect(screen.getByText('客户总量')).toBeInTheDocument()
    expect(screen.getByText('360')).toBeInTheDocument()
    expect(screen.getByText('当前先展示 6 位代表客户')).toBeInTheDocument()
    expect(screen.getByText('高净值 52')).toBeInTheDocument()
  })

  it('renders category overview instead of individual product cards', () => {
    render(
      <ProtocolRenderer
        component={{
          component_type: 'category_overview',
          component_id: 'category-overview-1',
          title: '当前可推荐品类',
          props: {
            total_categories: 3,
            items: [
              { category: '衬衫', product_count: 12, store_stock: 42 },
              { category: '西装', product_count: 8, store_stock: 20 },
            ],
          },
          actions: [],
        }}
        onAction={() => {}}
      />,
    )

    expect(screen.getByText('当前共有 3 个可推荐品类')).toBeInTheDocument()
    expect(screen.getByText('衬衫')).toBeInTheDocument()
    expect(screen.getByText('商品 12 款 · 门店现货 42 件')).toBeInTheDocument()
  })

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

  it('renders clarification notice with retry prompts', () => {
    render(
      <ProtocolRenderer
        component={{
          component_type: 'clarification_notice',
          component_id: 'clarify-1',
          title: '还需要补充一个关键信息',
          props: {
            reason: '当前还没有锁定具体客户。',
            prompts: ['帮我给乔安禾发条消息'],
          },
          actions: [
            {
              action_type: 'retry_send',
              label: '帮我给乔安禾发条消息',
              entity_type: 'conversation',
              method: 'POST',
              variant: 'secondary',
              payload: { message: '帮我给乔安禾发条消息' },
            },
          ],
        }}
        onAction={() => {}}
      />,
    )

    expect(screen.getByText('当前还没有锁定具体客户。')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '帮我给乔安禾发条消息' })).toBeInTheDocument()
  })
})
