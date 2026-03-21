import { expect, test } from '@playwright/test'

test('can run guided customer workflow and open detail', async ({ page }, testInfo) => {
  if (testInfo.project.name === 'mobile') {
    await page.goto('/crm')
    await expect(page.getByText('导购席位')).toBeVisible()
    await page.getByRole('button', { name: '帮我找今天该优先跟进但还没联系的高净值客户' }).click()
    await expect(page.getByText('正在整理本次客户建议')).toBeVisible()
    await expect(page.getByText('建议优先跟进客户')).toBeVisible()
    const customerCard = page.getByRole('button', { name: /客单累计/ }).first()
    await customerCard.scrollIntoViewIfNeeded()
    await customerCard.evaluate((node) => {
      ;(node as HTMLButtonElement).click()
    })
    await expect(page.getByText('客户概览')).toBeVisible()
    return
  }

  await page.goto('/crm')
  await page.getByRole('textbox').fill('帮我找今天该优先跟进但还没联系的高净值客户')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByText('正在整理本次客户建议')).toBeVisible()
  await expect(page.getByText('建议优先跟进客户')).toBeVisible()
  await page.getByRole('button', { name: '本轮节点' }).click()
  await expect(page.getByText('本轮节点')).toBeVisible()
  await page.getByRole('button', { name: /客单累计/ }).first().click()
  await expect(page.getByText('客户概览')).toBeVisible()
  await expect(page.getByText('已记录偏好与服务提示')).toBeVisible()
})

test('rejects out of domain questions', async ({ page }) => {
  await page.goto('/crm')
  await page.getByRole('textbox').fill('说说优衣库和政治新闻')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByText('当前仅支持导购域问题')).toBeVisible()
})

test('distinguishes customer inventory and category inventory queries', async ({ page }) => {
  await page.goto('/crm')
  await page.getByRole('textbox').fill('现在有哪些客户')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('heading', { name: '客户池概览' })).toBeVisible()
  await expect(page.getByText(/当前先展示 \d+ 位代表客户/)).toBeVisible()
  await expect(page.getByRole('heading', { name: '建议优先跟进客户' })).toBeVisible()

  await page.getByRole('textbox').fill('现在有哪些品类')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('heading', { name: '当前可推荐品类' }).last()).toBeVisible()
  await expect(page.getByText(/个可推荐品类/).last()).toBeVisible()
  await expect(page.getByText('衬衫')).toBeVisible()
})

test('keeps active customer across follow-up maintenance turns', async ({ page }) => {
  await page.goto('/crm')
  await page.getByRole('textbox').fill('我要维护一下乔安禾的客户关系')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('heading', { name: '本轮执行节奏' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '乔安禾 的维护建议' })).toBeVisible()
  await expect(page.getByText('维护打法')).toBeVisible()
  await expect(page.getByRole('heading', { name: '资深导购经验' })).toBeVisible()

  await page.getByRole('textbox').fill('你就按照他的喜好给我推荐维护关系的方式吧')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('heading', { name: '本轮执行节奏' }).last()).toBeVisible()
  await expect(page.getByRole('heading', { name: '乔安禾 的维护建议' }).last()).toBeVisible()
  await expect(page.getByText('维护打法')).toBeVisible()
  await expect(page.getByText('建议渠道')).toBeVisible()
  await expect(page.getByRole('heading', { name: '资深导购经验' }).last()).toBeVisible()
})

test('supports customer preference lookup and named message drafting', async ({ page }) => {
  await page.goto('/crm')

  await page.getByRole('textbox').fill('乔知夏喜欢什么')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('heading', { name: '客户偏好摘要' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '客户标签' })).toBeVisible()
  await expect(page.getByTestId('conversation-status-bar')).toBeVisible()
  await expect(page.getByTestId('status-task-type')).toHaveText('看客户画像')

  await page.getByRole('textbox').fill('帮我给乔安禾发条消息')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('heading', { name: '建议沟通话术' }).last()).toBeVisible()
  await expect(page.getByTestId('status-task-type')).toHaveText('整理沟通方式')
})

test('switches named customers without leaking previous context', async ({ page }) => {
  await page.goto('/crm')

  await page.getByRole('textbox').fill('乔安禾喜欢什么')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('button', { name: /乔安禾 黑金 极简层搭/ })).toBeVisible()

  await page.getByRole('textbox').fill('乔知夏喜欢什么')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('button', { name: /乔知夏/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /乔安禾 黑金 极简层搭/ })).toHaveCount(1)
})

test('shows understandable state during long follow-up chain', async ({ page }) => {
  await page.goto('/crm')

  await page.getByRole('textbox').fill('我要维护一下乔安禾的客户关系')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByTestId('conversation-status-bar')).toBeVisible()
  await expect(page.getByTestId('status-customer')).toHaveText('乔安禾')
  await expect(page.getByTestId('status-task-type')).toHaveText('整理维护方式')

  await page.getByRole('textbox').fill('按她的喜好推荐维护关系的方式')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByTestId('status-handoff-reason')).toContainText('本轮切换原因')

  await page.getByRole('textbox').fill('把今天到期还没完成的回访任务按优先级排一下')
  await page.getByTestId('composer-shell').getByRole('button', { name: '发送' }).click()
  await expect(page.getByTestId('status-task-type')).toHaveText('处理待办任务')
})
