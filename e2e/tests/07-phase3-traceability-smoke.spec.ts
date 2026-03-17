/**
 * E2E Flow 7: Phase-3 Traceability UI/API Smoke
 * - opens Test Planning
 * - opens first test case in edit mode
 * - verifies Scope/Governance section renders
 * - verifies derived + override endpoints are reachable
 */
import { test, expect } from '@playwright/test'
import { createTraceabilitySeed, openTraceabilityContext } from './helpers/traceability-seed'

test('phase3 ui: full-page test case detail renders traceability context', async ({ page, request }) => {
  const context = await createTraceabilitySeed(request, 'E2E Traceability')

  await openTraceabilityContext(page, context, {
    route: 'test-planning',
    user: {
      full_name: 'E2E Traceability User',
      email: 'traceability@example.com',
      roles: ['program_manager'],
    },
    waitForReady: false,
  })

  await expect(page.getByPlaceholder('Search test cases...')).toBeVisible({ timeout: 20000 })

  // Open first case detail from catalog table
  const caseRow = page
    .getByRole('row')
    .filter({ hasText: context.testCase.title })
    .first()
  await expect(caseRow).toBeVisible({ timeout: 20000 })
  await caseRow.click()

  await expect(page.locator('#tcDetailTabContent')).toBeVisible({ timeout: 20000 })
  const traceabilityTab = page.getByRole('button', { name: 'Traceability', exact: true })
  await expect(traceabilityTab).toBeVisible()
  await traceabilityTab.click()

  await expect(page.locator('#tcDetailTabContent')).toContainText('Derived Chain')
  await expect(page.locator('#tcDetailTabContent')).toContainText('Order to Cash')
  await expect(page.locator('#tcDetailTabContent')).toContainText('Dependencies')
})

test('phase3 api: derived and override endpoints are reachable', async ({ request }) => {
  const context = await createTraceabilitySeed(request, 'E2E Traceability')
  const tcId = context.testCase.id

  const derivedRes = await request.get(`/api/v1/testing/catalog/${tcId}/traceability-derived`)
  expect(derivedRes.ok()).toBeTruthy()
  const derived = await derivedRes.json()
  expect(derived).toHaveProperty('test_case_id')
  expect(derived).toHaveProperty('summary')

  // Minimal validation of override contract (intentionally invalid payload)
  const overrideRes = await request.put(`/api/v1/testing/catalog/${tcId}/traceability-overrides`, {
    data: {},
  })
  expect([400, 422]).toContain(overrideRes.status())
})
