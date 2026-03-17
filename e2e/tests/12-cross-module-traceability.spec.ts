/**
 * E2E Flow 12: Cross-module traceability — Explore ↔ Backlog ↔ Test
 */
import { test, expect } from '@playwright/test'
import {
  createCrossModuleTraceabilitySeed,
  openTraceabilityContext,
} from './helpers/traceability-seed'

test('traceability api exposes explore to backlog to test downstream chain', async ({ request }) => {
  const context = await createCrossModuleTraceabilitySeed(request, 'API')

  const exploreRes = await request.get(`/api/v1/traceability/explore_requirement/${context.requirement.id}`)
  expect(exploreRes.ok()).toBeTruthy()
  const exploreChain = await exploreRes.json()
  expect(JSON.stringify(exploreChain)).toContain(context.backlogItem.title)
  expect(JSON.stringify(exploreChain)).toContain(context.testCase.title)
  expect(JSON.stringify(exploreChain)).toContain(context.defect.title)

  const backlogRes = await request.get(`/api/v1/traceability/backlog_item/${context.backlogItem.id}`)
  expect(backlogRes.ok()).toBeTruthy()
  const backlogChain = await backlogRes.json()
  expect(JSON.stringify(backlogChain)).toContain(context.requirement.title)
  expect(JSON.stringify(backlogChain)).toContain(context.testCase.title)

  const testCaseRes = await request.get(`/api/v1/traceability/test_case/${context.testCase.id}`)
  expect(testCaseRes.ok()).toBeTruthy()
  const testCaseChain = await testCaseRes.json()
  expect((testCaseChain.upstream || []).some((item: any) => item.type === 'explore_requirement')).toBeTruthy()
  expect(JSON.stringify(testCaseChain)).toContain(context.requirement.title)
})

test('traceability ui shows the same chain in Explore, Backlog, and Test surfaces', async ({ page, request }) => {
  const context = await createCrossModuleTraceabilitySeed(request, 'UI')
  await openTraceabilityContext(page, context)

  await page.evaluate((reqId) => { TraceChain.show('explore_requirement', reqId) }, context.requirement.id)
  await expect(page.locator('#tcModalBody')).toContainText(context.requirement.title)
  await expect(page.locator('#tcModalBody')).toContainText(context.backlogItem.title)
  await expect(page.locator('#tcModalBody')).toContainText(context.testCase.title)
  await expect(page.locator('#tcModalBody')).toContainText(context.defect.title)
  await page.evaluate(() => { TraceChain.close() })

  await page.evaluate(() => {
    App.navigate('backlog')
  })
  await expect(page.locator('#backlogContent')).toBeVisible({ timeout: 20000 })
  await page.evaluate(async (backlogId) => {
    await BacklogView.openDetail(backlogId)
    BacklogView.renderDetail()
  }, context.backlogItem.id)
  await expect(page.locator('#detailTabContent')).toBeVisible({ timeout: 20000 })
  await page.evaluate(() => { BacklogView.switchDetailTab('trace') })
  await expect(page.locator('#detailTabContent')).toContainText(context.requirement.title)
  await expect(page.locator('#detailTabContent')).toContainText(context.testCase.title)
  await expect(page.locator('#detailTabContent')).toContainText(context.defect.title)

  await page.evaluate(async (testCaseId) => {
    if (typeof TestingShared !== 'undefined' && TestingShared.getProgram) {
      TestingShared.getProgram()
    }
    await TestCaseDetailView.render(testCaseId)
  }, context.testCase.id)
  await expect(page.locator('#tcDetailTabContent')).toBeVisible({ timeout: 20000 })
  await page.evaluate(() => { TestCaseDetailView.switchTab('traceability') })
  await expect(page.locator('#tcDetailTabContent')).toContainText('Derived Chain')
  await expect(page.locator('#tcDetailTabContent')).toContainText(context.requirement.code)
  await expect(page.locator('#tcDetailTabContent')).toContainText('Process')
})

test('traceability workflow shows defect upstream chain back to explore assets', async ({ page, request }) => {
  const context = await createCrossModuleTraceabilitySeed(request, 'Defect Chain')
  await openTraceabilityContext(page, context)

  await page.evaluate((defectId) => { TraceChain.show('defect', defectId) }, context.defect.id)
  await expect(page.locator('#tcModalBody')).toContainText(context.defect.title)
  await expect(page.locator('#tcModalBody')).toContainText(context.testCase.title)
  await expect(page.locator('#tcModalBody')).toContainText(context.backlogItem.title)
  await expect(page.locator('#tcModalBody')).toContainText(context.requirement.title)
})

test('traceability workflow deep-links from chain nodes into backlog, test, and defect workspaces', async ({ page, request }) => {
  const context = await createCrossModuleTraceabilitySeed(request, 'Deep Link')
  await openTraceabilityContext(page, context)

  await page.evaluate((defectId) => { TraceChain.show('defect', defectId) }, context.defect.id)
  await expect(page.locator('#tcModalBody')).toContainText(context.backlogItem.title)

  await page.evaluate((backlogId) => { TraceChain._navigate('backlog_item', backlogId) }, context.backlogItem.id)
  await expect(page.locator('#detailTabContent')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('#detailTabContent')).toContainText(context.testCase.title)

  await page.evaluate((testCaseId) => { TraceChain._navigate('test_case', testCaseId) }, context.testCase.id)
  await expect(page.locator('#tcDetailTabContent')).toBeVisible({ timeout: 20000 })
  await page.evaluate(() => { TestCaseDetailView.switchTab('traceability') })
  await expect(page.locator('#tcDetailTabContent')).toContainText(context.requirement.code)

  await page.evaluate((defectId) => { TraceChain._navigate('defect', defectId) }, context.defect.id)
  await expect(page.locator('body')).toContainText('Defect → Retest → Approval Chain')
})
