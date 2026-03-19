import { expect, test } from '@playwright/test'

test('can run guided customer workflow and open detail', async ({ page }, testInfo) => {
  if (testInfo.project.name === 'mobile') {
    await page.goto('/crm')
    await expect(page.getByText('缦序 导购席位')).toBeVisible()
    await page.getByRole('button', { name: '帮我找今天该优先跟进但还没联系的高净值客户' }).click()
    await expect(page.getByText('建议优先跟进客户')).toBeVisible()
    await page.getByRole('button', { name: /客单累计/ }).first().click()
    await expect(page.getByText('客户概览')).toBeVisible()
    return
  }

  await page.goto('/crm')
  await page.getByPlaceholder('例如：帮我找今天该优先跟进但还没联系的高净值客户').fill('把今天到期还没完成的回访任务按优先级排一下')
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByText('待处理任务')).toBeVisible()
  await page.getByRole('button', { name: /^完成$/ }).first().click()
  await expect(page.getByText('任务已标记完成，并同步更新到工作台。')).toBeVisible()
})

test('rejects out of domain questions', async ({ page }) => {
  await page.goto('/crm')
  await page.getByPlaceholder('例如：帮我找今天该优先跟进但还没联系的高净值客户').fill('说说优衣库和政治新闻')
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByText('当前仅支持导购域问题')).toBeVisible()
})
