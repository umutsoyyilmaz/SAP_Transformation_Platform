/**
 * E2E Flow 6: FE-Sprint 3 Smoke Tests — isolated, self-seeded variant.
 * Covers sidebar, Explore, Test Hub APIs, and stale dashboard request guards.
 */
import { test, expect, APIRequestContext, Page } from '@playwright/test'
import { openWithActiveContext } from './helpers/active-context'
import { createTestingSmokeSeed } from './helpers/testing-seed'

type SmokeContext = {
  program: Record<string, any>
  project: Record<string, any>
  l3: Record<string, any>
  plan: Record<string, any>
  cycle: Record<string, any>
  testCase: Record<string, any>
  suite: Record<string, any>
  defect: Record<string, any>
  backlogItem: Record<string, any>
}

let smokeContext: SmokeContext

async function createSmokeContext(request: APIRequestContext): Promise<SmokeContext> {
  return createTestingSmokeSeed(request, {
    label: 'FE Sprint3',
    methodology: 'sap_activate',
    module: 'MM',
    l3CodePrefix: 'MM',
    l3Name: 'Materials Management',
    fitStatus: 'fit',
    testLayer: 'sit',
    planEnvironment: 'QAS',
  })
}

async function openWithContext(page: Page, context: SmokeContext, route?: string) {
  await openWithActiveContext(page, context, {
    route,
    user: {
      full_name: 'E2E FE Sprint3 User',
      email: 'fe-sprint3@example.com',
      roles: ['program_manager'],
    },
  })
}

test.beforeAll(async ({ request }) => {
  smokeContext = await createSmokeContext(request)
})

/* ─── 1-3: SIDEBAR CLEANUP ──────────────────────────────── */

test('01 — sidebar: old scope items removed', async ({ page }) => {
  await openWithContext(page, smokeContext)
  const sidebar = page.locator('#sidebar')
  await expect(sidebar.getByText('Scenarios', { exact: true })).not.toBeVisible()
  await expect(sidebar.getByText('Analysis Hub', { exact: true })).not.toBeVisible()
})

test('02 — sidebar: explore group visible', async ({ page }) => {
  await openWithContext(page, smokeContext)
  const sidebar = page.locator('#sidebar')
  await expect(sidebar.getByText('Discover', { exact: true })).toBeVisible()
  await expect(sidebar.getByText('Explore', { exact: true })).toBeVisible()
})

test('03 — sidebar: delivery group visible', async ({ page }) => {
  await openWithContext(page, smokeContext)
  const sidebar = page.locator('#sidebar')
  await expect(sidebar.getByText('Build', { exact: true })).toBeVisible()
  await expect(sidebar.getByText('Test', { exact: true })).toBeVisible()
  await expect(sidebar.getByText('Release', { exact: true })).toBeVisible()
})

/* ─── 4-6: EXPLORE PHASE ────────────────────────────────── */

test('04 — explore dashboard loads', async ({ page }) => {
  await openWithContext(page, smokeContext, 'explore-overview')
  await expect(page.locator('#mainContent')).toBeVisible()
})

test('05 — explore workshops list loads', async ({ request }) => {
  const res = await request.get(`/api/v1/explore/workshops?project_id=${smokeContext.project.id}`)
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const items = body.items || body
  expect(Array.isArray(items)).toBeTruthy()
})

test('06 — explore workshop detail: no stubs', async ({ request }) => {
  const listRes = await request.get(`/api/v1/explore/workshops?project_id=${smokeContext.project.id}`)
  expect(listRes.ok()).toBeTruthy()
  const listBody = await listRes.json()
  const items = listBody.items || listBody
  if (items.length > 0) {
    const wsId = items[0].id
    const detailRes = await request.get(`/api/v1/explore/workshops/${wsId}`)
    expect(detailRes.ok()).toBeTruthy()
    const detail = await detailRes.json()
    expect(detail.id).toBe(wsId)
  }
})

/* ─── 7-9: TEST HUB — SUITE & CATALOG (FE-Sprint 1) ───── */

test('07 — test hub: suites tab visible', async ({ page }) => {
  await openWithContext(page, smokeContext, 'test-planning')
  await expect(page.getByRole('button', { name: /Test Suites/ })).toBeVisible()
})

test('08 — test hub: suites API works', async ({ request }) => {
  const res = await request.get(`/api/v1/programs/${smokeContext.program.id}/testing/suites`)
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const items = body.items || body
  expect(Array.isArray(items)).toBeTruthy()
  expect(items.some((item: any) => item.id === smokeContext.suite.id)).toBeTruthy()
})

test('09 — test hub: catalog API with dependency counts', async ({ request }) => {
  const res = await request.get(`/api/v1/programs/${smokeContext.program.id}/testing/catalog`)
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const items = body.items || body
  expect(Array.isArray(items)).toBeTruthy()
  const seededCase = items.find((item: any) => item.id === smokeContext.testCase.id)
  expect(seededCase).toBeTruthy()
  expect(seededCase).toHaveProperty('blocked_by_count')
  expect(seededCase).toHaveProperty('blocks_count')
})

/* ─── 10-11: TEST HUB — DEFECT DETAIL (FE-Sprint 2) ────── */

test('10 — defect detail: comments API works', async ({ request }) => {
  const commentsRes = await request.get(`/api/v1/testing/defects/${smokeContext.defect.id}/comments`)
  expect(commentsRes.ok()).toBeTruthy()
  const comments = await commentsRes.json()
  expect(Array.isArray(comments)).toBeTruthy()
  expect(comments.length).toBeGreaterThanOrEqual(1)
})

test('11 — defect detail: history API works', async ({ request }) => {
  const histRes = await request.get(`/api/v1/testing/defects/${smokeContext.defect.id}/history`)
  expect(histRes.ok()).toBeTruthy()
  const history = await histRes.json()
  expect(Array.isArray(history)).toBeTruthy()
})

/* ─── 12-15: TEST HUB — FE-Sprint 3 FEATURES ────────────── */

test('12 — SLA endpoint works for defect', async ({ request }) => {
  const slaRes = await request.get(`/api/v1/testing/defects/${smokeContext.defect.id}/sla`)
  expect(slaRes.ok()).toBeTruthy()
  const sla = await slaRes.json()
  expect(sla).toHaveProperty('sla_status')
  expect(sla).toHaveProperty('defect_id')
  expect(sla.defect_id).toBe(smokeContext.defect.id)
})

test('13 — Go/No-Go scorecard API works', async ({ request }) => {
  const res = await request.get(`/api/v1/programs/${smokeContext.program.id}/testing/dashboard/go-no-go`)
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  expect(body).toHaveProperty('overall')
  expect(body).toHaveProperty('scorecard')
  expect(Array.isArray(body.scorecard)).toBeTruthy()
  expect(body.scorecard.length).toBeGreaterThan(0)
})

test('14 — Generate from WRICEF endpoint exists', async ({ request }) => {
  const res = await request.post(`/api/v1/testing/suites/${smokeContext.suite.id}/generate-from-wricef`, {
    data: { wricef_item_ids: [smokeContext.backlogItem.id] },
  })
  expect([200, 201]).toContain(res.status())
  const body = await res.json()
  expect(body).toHaveProperty('count')
})

test('15 — UAT sign-off endpoint exists', async ({ request }) => {
  const res = await request.get(`/api/v1/testing/uat-signoffs?cycle_id=${smokeContext.cycle.id}`)
  expect([200, 404]).toContain(res.status())
})

/* ─── 16: DASHBOARD — NO STALE API CALLS ─────────────────── */

test('16 — dashboard does not call old scope APIs', async ({ page }) => {
  const requests: string[] = []
  page.on('request', (req) => requests.push(req.url()))

  await openWithContext(page, smokeContext, 'dashboard')
  await page.waitForTimeout(1500)

  const oldCalls = requests.filter(
    (url) => url.includes('/scenarios') || url.includes('/process-hierarchy')
  )
  expect(oldCalls).toHaveLength(0)
})
