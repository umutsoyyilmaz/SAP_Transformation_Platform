/**
 * E2E Flow 10: Test Management — operations-first IA smoke
 */
import { test, expect, APIRequestContext, Page } from '@playwright/test'
import { createProgramContext } from './helpers/seed-factory'

type AuthPayload = {
  access_token: string
  refresh_token: string
  user: Record<string, any>
}

function buildFakeJwt() {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({
    sub: 'e2e-smoke',
    tenant_id: 1,
    exp: Math.floor(Date.now() / 1000) + 60 * 60,
  })).toString('base64url')
  return `${header}.${payload}.signature`
}

async function loginSeededUser(request: APIRequestContext): Promise<AuthPayload | null> {
  const tenantRes = await request.get('/api/v1/auth/tenants')
  if (!tenantRes.ok()) return null
  const tenants = await tenantRes.json()
  const tenantSlugs = Array.isArray(tenants) ? tenants.map((t: any) => t.slug) : []

  const loginCandidates = [
    { email: 'admin@anadolu.com', password: 'Anadolu2026!', tenant_slug: 'anadolu-gida' },
    { email: 'pm@anadolu.com', password: 'Test1234!', tenant_slug: 'anadolu-gida' },
    { email: 'viewer@demo.com', password: 'Demo1234!', tenant_slug: 'demo' },
  ].filter((candidate) => tenantSlugs.includes(candidate.tenant_slug))

  for (const candidate of loginCandidates) {
    const loginRes = await request.post('/api/v1/auth/login', { data: candidate })
    if (!loginRes.ok()) continue
    const payload = await loginRes.json()
    if (payload?.access_token && payload?.refresh_token && payload?.user) return payload
  }
  return null
}

async function resolveTestingContext(request: APIRequestContext, auth: AuthPayload) {
  const headers = auth?.access_token ? { Authorization: `Bearer ${auth.access_token}` } : undefined
  for (const programId of [1, 2, 3, 4, 5, 10, 20]) {
    let programRes = await request.get(`/api/v1/programs/${programId}`, headers ? { headers } : undefined)
    if (!programRes.ok() && headers) {
      programRes = await request.get(`/api/v1/programs/${programId}`)
    }
    if (!programRes.ok()) continue
    const program = await programRes.json()

    let projectsRes = await request.get(
      `/api/v1/programs/${program.id}/projects`,
      headers ? { headers } : undefined,
    )
    if (!projectsRes.ok() && headers) {
      projectsRes = await request.get(`/api/v1/programs/${program.id}/projects`)
    }
    if (!projectsRes.ok()) continue
    const projectsBody = await projectsRes.json()
    const projects = projectsBody.items || projectsBody
    if (!Array.isArray(projects) || projects.length === 0) continue

    let plansRes = await request.get(
      `/api/v1/programs/${program.id}/testing/plans`,
      headers ? { headers } : undefined,
    )
    if (!plansRes.ok() && headers) {
      plansRes = await request.get(`/api/v1/programs/${program.id}/testing/plans`)
    }
    if (!plansRes.ok()) continue
    const plansBody = await plansRes.json()
    const plans = plansBody.items || plansBody
    if (Array.isArray(plans)) {
      return { program, project: projects[0], plans }
    }
  }
  return null
}

async function createTestingContext(request: APIRequestContext) {
  const { program, project } = await createProgramContext(request, {
    namePrefix: 'E2E TM Smoke',
    methodology: 'agile',
  })

  const createPlanRes = await request.post(`/api/v1/programs/${program.id}/testing/plans`, {
    data: {
      name: 'E2E Smoke Plan',
      description: 'Deterministic Playwright smoke context',
      plan_type: 'sit',
    },
  })
  expect(createPlanRes.ok()).toBeTruthy()
  const plan = await createPlanRes.json()

  const createCycleRes = await request.post(`/api/v1/testing/plans/${plan.id}/cycles`, {
    data: {
      name: 'E2E Smoke Cycle',
      test_layer: 'sit',
    },
  })
  expect(createCycleRes.ok()).toBeTruthy()

  return {
    program,
    project,
    plans: [plan],
  }
}

async function bootstrapTestingContext(page: Page, auth: AuthPayload, context: { program: any, project: any }) {
  const fakeToken = buildFakeJwt()
  const fallbackUser = auth?.user || {
    id: 0,
    full_name: 'E2E Smoke User',
    email: 'e2e@example.com',
    tenant_id: context.program.tenant_id || 1,
  }
  await page.route(`**/api/v1/programs/${context.program.id}/projects`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([context.project]),
    })
  })
  await page.context().addInitScript(({ payload, activeContext }) => {
    if (payload.access_token) localStorage.setItem('sap_access_token', payload.access_token)
    if (payload.refresh_token) localStorage.setItem('sap_refresh_token', payload.refresh_token)
    localStorage.setItem('sap_user', JSON.stringify(payload.user))
    localStorage.setItem('sap_active_program', JSON.stringify({
      id: activeContext.program.id,
      name: activeContext.program.name,
      status: activeContext.program.status || 'active',
      project_type: activeContext.program.project_type || 'sap_activate',
      tenant_id: payload.user.tenant_id,
    }))
    localStorage.setItem('sap_active_project', JSON.stringify({
      id: activeContext.project.id,
      name: activeContext.project.name,
      code: activeContext.project.code,
      program_id: activeContext.program.id,
      tenant_id: payload.user.tenant_id,
    }))
  }, {
    payload: {
      access_token: auth?.access_token || fakeToken,
      refresh_token: auth?.refresh_token || fakeToken,
      user: fallbackUser,
    },
    activeContext: context,
  })
}

test('test management operational APIs stay reachable', async ({ request }) => {
  const context = await createTestingContext(request)

  const plansRes = await request.get(`/api/v1/programs/${context.program.id}/testing/plans`)
  expect(plansRes.ok()).toBeTruthy()

  const defectsRes = await request.get(`/api/v1/programs/${context.program.id}/testing/defects`)
  expect(defectsRes.ok()).toBeTruthy()

  const cycleRiskRes = await request.get(`/api/v1/programs/${context.program.id}/testing/dashboard/cycle-risk`)
  expect(cycleRiskRes.ok()).toBeTruthy()
})

test('test management ui exposes operations-first flow', async ({ page, request }) => {
  const auth = await loginSeededUser(request)
  const context = await resolveTestingContext(request, auth as AuthPayload)
    || await createTestingContext(request)

  await bootstrapTestingContext(page, auth as AuthPayload, context as { program: any, project: any })
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await expect(page.locator('#sidebar [data-view=\"programs\"]')).toBeVisible({ timeout: 20000 })
  await page.evaluate((activeContext) => {
    localStorage.setItem('sap_active_program', JSON.stringify({
      id: activeContext.program.id,
      name: activeContext.program.name,
      status: activeContext.program.status || 'active',
      project_type: activeContext.program.project_type || 'sap_activate',
      tenant_id: activeContext.program.tenant_id || 1,
    }))
    localStorage.setItem('sap_active_project', JSON.stringify({
      id: activeContext.project.id,
      name: activeContext.project.name,
      code: activeContext.project.code,
      program_id: activeContext.program.id,
      tenant_id: activeContext.project.tenant_id || activeContext.program.tenant_id || 1,
    }))
    localStorage.setItem('sap_user', JSON.stringify({
      id: 999,
      full_name: 'TM E2E Manager',
      email: 'tm-e2e@example.com',
      tenant_id: activeContext.program.tenant_id || 1,
      roles: ['test_manager'],
    }))
    if (typeof App !== 'undefined' && App.updateProgramBadge) {
      App.updateProgramBadge()
    }
    if (typeof App !== 'undefined' && App.updateSidebarState) {
      App.updateSidebarState()
    }
  }, context)
  await expect.poll(async () => {
    return await page.evaluate(() => typeof App !== 'undefined' && Boolean(App.navigate))
  }).toBeTruthy()

  await page.evaluate(() => { App.navigate('test-overview') })
  await expect(page.locator('[data-testid="test-overview-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('heading', { name: 'Test Overview' })).toBeVisible()
  await expect(page.locator('[data-testid="test-overview-page"]')).toContainText('Execution Center')
  await expect(page.locator('[data-testid="test-overview-page"]')).toContainText('Defects & Retest')
  await expect(page.locator('[data-testid="role-cockpit-panel"]')).toContainText('Test Manager Cockpit')

  await page.evaluate(() => { App.navigate('test-manager-cockpit') })
  await expect(page.locator('[data-testid="role-workspace-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('heading', { name: 'Test Manager Cockpit' })).toBeVisible()
  await expect(page.locator('[data-testid="role-workspace-checklist"]')).toContainText('pending approvals')
  await expect(page.locator('[data-testid="manager-risk-board"]')).toBeVisible()

  await page.evaluate(() => { App.navigate('test-lead-cockpit') })
  await expect(page.getByRole('heading', { name: 'SIT / UAT Lead Cockpit' })).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="lead-ops-board"]')).toBeVisible()

  await page.evaluate(() => { App.navigate('business-tester-workspace') })
  await expect(page.getByRole('heading', { name: 'Business Tester Workspace' })).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="business-approval-board"]')).toBeVisible()

  await page.evaluate(() => { App.navigate('execution-center') })
  await expect(page.locator('[data-testid="execution-center-ops"]')).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('heading', { name: 'Execution Center' })).toBeVisible()
  await expect(page.locator('[data-testid="execution-center-ops"]')).toContainText('Ready or deferred executions')
  await expect(page.locator('#testExecTabs')).toContainText('My Queue')
  await expect(page.locator('#testExecTabs')).toContainText('Retest')

  await page.evaluate(() => { App.navigate('defects-retest') })
  await expect(page.getByRole('heading', { name: 'Defects & Retest' })).toBeVisible({ timeout: 20000 })
  await expect(page.locator('#mainContent')).toContainText('Report Defect')

  await page.evaluate(() => { App.navigate('signoff-approvals') })
  await expect(page.getByRole('heading', { name: 'Approvals & Sign-off' })).toBeVisible({ timeout: 20000 })
  await expect(page.locator('#mainContent')).toContainText('Pending')
})
