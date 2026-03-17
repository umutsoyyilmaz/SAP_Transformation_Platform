/**
 * E2E Flow 11: Test Management — workflow scenarios beyond smoke
 */
import { test, expect, APIRequestContext, Page } from '@playwright/test'
import { createApprovalWorkflow } from './helpers/approval-seed'
import { createDefect, createTestingSmokeSeed, createTestingWorkflowSeed } from './helpers/testing-seed'

type AuthPayload = {
  access_token: string
  refresh_token: string
  user: Record<string, any>
}

type WorkflowContext = {
  program: Record<string, any>
  project: Record<string, any>
  plan: Record<string, any>
  cycle: Record<string, any>
  testCase: Record<string, any>
  execution: Record<string, any>
}

type BaseTestingContext = Pick<WorkflowContext, 'program' | 'project'>

function buildFakeJwt() {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({
    sub: 'e2e-tm-workflow',
    tenant_id: 1,
    exp: Math.floor(Date.now() / 1000) + 60 * 60,
  })).toString('base64url')
  return `${header}.${payload}.signature`
}

async function createWorkflowContext(request: APIRequestContext, label: string): Promise<WorkflowContext> {
  const context = await createTestingWorkflowSeed(request, { label })
  const { program, project, plan, cycle, testCase, execution } = context
  return { program, project, plan, cycle, testCase, execution }
}

async function bootstrapTestingContext(page: Page, context: BaseTestingContext, role: string) {
  const fakeToken = buildFakeJwt()
  await page.route(`**/api/v1/programs/${context.program.id}/projects`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([context.project]),
    })
  })
  await page.context().addInitScript(({ token, activeContext, activeRole }) => {
    localStorage.setItem('sap_access_token', token)
    localStorage.setItem('sap_refresh_token', token)
    localStorage.setItem('sap_user', JSON.stringify({
      id: 990,
      full_name: 'TM Workflow User',
      email: 'tm-workflow@example.com',
      tenant_id: activeContext.program.tenant_id || 1,
      roles: [activeRole],
    }))
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
  }, { token: fakeToken, activeContext: context, activeRole: role })

  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await expect(page.locator('#sidebar [data-view="programs"]')).toBeVisible({ timeout: 20000 })
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
    if (typeof App !== 'undefined' && App.updateProgramBadge) App.updateProgramBadge()
    if (typeof App !== 'undefined' && App.updateSidebarState) App.updateSidebarState()
  }, context)
  await expect.poll(async () => {
    return await page.evaluate(() => typeof App !== 'undefined' && Boolean(App.navigate))
  }).toBeTruthy()
}

test('workflow: defect to approval approval-chain closes end-to-end', async ({ page, request }) => {
  const context = await createWorkflowContext(request, 'Approval Flow')

  await createApprovalWorkflow(request, context.program.id, {
    name: 'E2E TC Workflow',
    stages: [{ stage: 1, role: 'QA Lead', required: true }],
  })

  await bootstrapTestingContext(page, context, 'test_manager')

  await page.evaluate(() => {
    App.navigate('defects-retest')
  })
  await expect(page.getByRole('heading', { name: 'Defects & Retest' })).toBeVisible({ timeout: 20000 })
  await page.evaluate(() => { DefectManagementView.showDefectModal() })
  await expect(page.getByRole('heading', { name: 'Defects & Retest' })).toBeVisible({ timeout: 20000 })
  await expect(page.locator('#modalContainer h2')).toContainText('Report Defect')

  const defectTitle = `Workflow defect ${Date.now()}`
  await page.fill('#defTitle', defectTitle)
  await page.fill('#defDesc', 'Raised from execution workflow E2E')
  await page.fill('#defTestCaseId', String(context.testCase.id))
  await page.fill('#defModule', 'FI')
  await page.fill('#defReporter', 'E2E Tester')
  await page.click('#modalContainer .modal-footer .btn.btn-primary')

  await expect.poll(async () => {
    const res = await request.get(`/api/v1/programs/${context.program.id}/testing/defects`)
    const payload = await res.json()
    const list = payload?.items || payload || []
    return (list || []).find((item: any) => item.title === defectTitle) || null
  }).not.toBeNull()
  const defectsRes = await request.get(`/api/v1/programs/${context.program.id}/testing/defects`)
  const defectsPayload = await defectsRes.json()
  const defectsList = defectsPayload?.items || defectsPayload || []
  const defect = defectsList.find((item: any) => item.title === defectTitle)
  expect(defect?.id).toBeTruthy()

  await page.evaluate((defectId) => { DefectManagementView.showDefectDetail(defectId) }, (defect as any).id)
  await expect(page.locator('body')).toContainText('Defect → Retest → Approval Chain')
  await expect(page.locator('#defectApprovalBanner')).toContainText('Not submitted for approval')
  await page.click('#defectApprovalBanner button')
  await expect(page.locator('#defectApprovalBanner')).toContainText('Approval Status:')
  await expect(page.locator('#defectApprovalBanner')).toContainText('PENDING')

  await page.evaluate(() => { App.navigate('signoff-approvals') })
  await expect(page.getByRole('heading', { name: 'Approvals & Sign-off' })).toBeVisible({ timeout: 20000 })
  await expect(page.locator('#mainContent')).toContainText('test_case')
  await page.getByRole('button', { name: 'Approve' }).first().click()
  await expect(page.locator('#mainContent')).toContainText('No pending approvals')

  await page.evaluate((defectId) => {
    App.navigate('defects-retest')
    setTimeout(() => DefectManagementView.showDefectDetail(defectId), 80)
  }, (defect as any).id)
  await expect(page.locator('#defectApprovalBanner')).toContainText('Approval Status:')
  await expect(page.locator('#defectApprovalBanner')).toContainText('APPROVED')
})

test('workflow: retest queue opens execution and auto-derives pass from step results', async ({ page, request }) => {
  const context = await createWorkflowContext(request, 'Retest Flow')

  await createDefect(request, {
    programId: context.program.id,
    title: 'Retest-ready defect',
    severity: 'S2',
    status: 'resolved',
    executionId: context.execution.id,
    module: 'FI',
  })

  await bootstrapTestingContext(page, context, 'test_lead')

  await page.evaluate(() => { App.navigate('execution-center') })
  await expect(page.getByRole('heading', { name: 'Execution Center' })).toBeVisible({ timeout: 20000 })
  await page.evaluate(() => { TestExecutionView.switchTab('retest') })
  await expect(page.locator('#mainContent')).toContainText('Retest-ready defect')
  await page.evaluate((args) => { TestExecutionView.openExecStepExecution(args.execId, args.cycleId) }, {
    execId: context.execution.id,
    cycleId: context.cycle.id,
  })
  await expect(page.locator('#modalContainer')).toContainText('Step-by-Step Execution')
  await page.getByRole('button', { name: /All Pass/i }).click()
  await page.getByRole('button', { name: /Save & Auto-Derive Result/i }).click()

  await expect.poll(async () => {
    const res = await request.get(`/api/v1/testing/executions/${context.execution.id}`)
    const execution = await res.json()
    return execution.result
  }).toBe('pass')
})

test('workflow: suite quick-run opens execution center and case-detail deep-link stays in context', async ({ page, request }) => {
  const context = await createTestingSmokeSeed(request, {
    label: 'Quick Run Gate',
    testLayer: 'unit',
    module: 'FI',
  })

  await bootstrapTestingContext(page, context, 'test_manager')

  await page.evaluate(() => { App.navigate('test-planning') })
  await expect.poll(async () => {
    return await page.evaluate(() => typeof TestPlanningView !== 'undefined' && typeof TestPlanningView.showSuiteDetail === 'function')
  }).toBeTruthy()
  await page.evaluate((suiteId) => { TestPlanningView.showSuiteDetail(suiteId) }, context.suite.id)
  await expect(page.locator(`#btnQuickRun_${context.suite.id}`)).toBeVisible({ timeout: 20000 })
  await page.click(`#btnQuickRun_${context.suite.id}`)
  await expect(page.getByRole('heading', { name: 'Execution Center' })).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="execution-center-ops"]')).toContainText('Ready or deferred executions')

  await page.goto(`/#test-case-detail/${context.testCase.id}/tab/executions`)
  await expect(page).toHaveURL(new RegExp(`#test-case-detail/${context.testCase.id}/tab/executions$`))
  await expect(page.locator('#mainContent')).toContainText('Execute This Test Case')
  await expect(page.locator('#mainContent')).toContainText('Executions')
})

test('workflow: evidence gallery renders in mainContent and add flow works end-to-end', async ({ page, request }) => {
  const context = await createWorkflowContext(request, 'Evidence Flow')

  await bootstrapTestingContext(page, context, 'test_lead')

  await page.evaluate((executionId) => { TestExecutionView.openExecutionEvidence(executionId) }, context.execution.id)
  await expect(page.locator('#mainContent .f8e-layout')).toHaveCount(1, { timeout: 20000 })
  await expect(page.locator('body > .f8e-layout')).toHaveCount(0)
  await expect(page.locator('#mainContent')).toContainText('Evidence Gallery')

  await page.click('#f8e-add')
  await page.fill('#f8em-name', 'epic7-evidence.png')
  await page.fill('#f8em-path', '/storage/evidence/epic7-evidence.png')
  await page.fill('#f8em-size', '1024')
  await page.fill('#f8em-mime', 'image/png')
  await page.fill('#f8em-desc', 'Epic 7 evidence gate')
  await page.click('#f8em-save')
  await expect(page.locator('#f8e-gallery')).toContainText('epic7-evidence.png')
})
