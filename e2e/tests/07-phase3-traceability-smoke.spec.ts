/**
 * E2E Flow 7: Phase-3 Traceability UI/API Smoke
 * - opens Test Planning
 * - opens first test case in edit mode
 * - verifies Scope/Governance section renders
 * - verifies derived + override endpoints are reachable
 */
import { test, expect } from '@playwright/test'

test('phase3 ui: full-page test case detail renders traceability context', async ({ page, request }) => {
  const listRes = await request.get('/api/v1/programs/1/testing/catalog')
  expect(listRes.ok()).toBeTruthy()
  const listBody = await listRes.json()
  const items = listBody.items || listBody
  test.skip(!Array.isArray(items) || items.length === 0, 'No test case found for project 1')

  const tenantRes = await request.get('/api/v1/auth/tenants')
  expect(tenantRes.ok()).toBeTruthy()
  const tenants = await tenantRes.json()
  const tenantSlugs = Array.isArray(tenants) ? tenants.map((t: any) => t.slug) : []

  const loginCandidates = [
    { email: 'admin@anadolu.com', password: 'Anadolu2026!', tenant_slug: 'anadolu-gida' },
    { email: 'pm@anadolu.com', password: 'Test1234!', tenant_slug: 'anadolu-gida' },
    { email: 'viewer@demo.com', password: 'Demo1234!', tenant_slug: 'demo' },
  ].filter(c => tenantSlugs.includes(c.tenant_slug))

  let authPayload: any = null
  for (const candidate of loginCandidates) {
    const loginRes = await request.post('/api/v1/auth/login', { data: candidate })
    if (!loginRes.ok()) continue
    const data = await loginRes.json()
    if (data?.access_token && data?.refresh_token && data?.user) {
      authPayload = data
      break
    }
  }

  test.skip(!authPayload, 'No valid seeded test user found for login')

  await page.addInitScript((payload) => {
    localStorage.setItem('sap_access_token', payload.access_token)
    localStorage.setItem('sap_refresh_token', payload.refresh_token)
    localStorage.setItem('sap_user', JSON.stringify(payload.user))
    localStorage.setItem('sap_active_program', JSON.stringify({
      id: 1,
      name: 'Program 1',
      status: 'active',
      project_type: 'agile',
    }))
  }, authPayload)

  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.locator('[data-view="test-planning"]').first().click({ force: true })
  await page.waitForLoadState('networkidle')

  const catalogArea = page.locator('#catalogTableArea')
  await expect(catalogArea).toBeVisible({ timeout: 20000 })

  // Open first case detail from catalog table
  const firstRow = page.locator('#catalogTableArea tbody tr').first()
  await expect(firstRow).toBeVisible({ timeout: 20000 })
  await firstRow.click()

  await expect(page.locator('#tcDetailTabContent')).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('button', { name: 'Traceability' })).toBeVisible()
  await page.getByRole('button', { name: 'Traceability' }).click()

  await expect(page.locator('#tcDetailTabContent')).toContainText('Derived Chain Summary')
  await expect(page.locator('#tcDetailTabContent')).toContainText('Dependencies')
})

test('phase3 api: derived and override endpoints are reachable', async ({ request }) => {
  const listRes = await request.get('/api/v1/programs/1/testing/catalog')
  expect(listRes.ok()).toBeTruthy()
  const listBody = await listRes.json()
  const items = listBody.items || listBody
  test.skip(!Array.isArray(items) || items.length === 0, 'No test case found for project 1')

  const tcId = items[0].id

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
