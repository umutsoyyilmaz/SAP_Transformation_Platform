import { expect, Page } from '@playwright/test'

type ProgramRecord = Record<string, any>
type ProjectRecord = Record<string, any>

export type ActiveProgramProjectContext = {
  program: ProgramRecord
  project?: ProjectRecord | null
}

type ActiveContextUserOptions = {
  id?: number
  full_name?: string
  email?: string
  roles?: string[]
}

export type ActiveContextOptions = {
  user?: ActiveContextUserOptions
  route?: string
  useAppSetters?: boolean
  waitForProjectSync?: boolean
  expectProjectId?: number | null
}

function _buildPayload(
  context: ActiveProgramProjectContext,
  options: ActiveContextOptions = {},
) {
  return {
    context,
    options: {
      route: options.route || null,
      useAppSetters: options.useAppSetters === true,
      waitForProjectSync: options.waitForProjectSync !== false,
      expectProjectId: options.expectProjectId ?? context.project?.id ?? null,
      user: {
        id: options.user?.id ?? 0,
        full_name: options.user?.full_name ?? 'E2E User',
        email: options.user?.email ?? 'e2e@example.com',
        roles: options.user?.roles ?? ['program_manager'],
      },
    },
  }
}

export async function primeActiveContext(
  page: Page,
  context: ActiveProgramProjectContext,
  options: ActiveContextOptions = {},
) {
  const payload = _buildPayload(context, options)
  await page.addInitScript((browserPayload) => {
    const activeContext = browserPayload.context
    const opts = browserPayload.options
    const tenantId = activeContext.program.tenant_id || activeContext.project?.tenant_id || 1
    const program = {
      id: activeContext.program.id,
      name: activeContext.program.name,
      status: activeContext.program.status || 'active',
      project_type: activeContext.program.project_type || 'sap_activate',
      tenant_id: tenantId,
    }
    const project = activeContext.project ? {
      id: activeContext.project.id,
      name: activeContext.project.name,
      code: activeContext.project.code,
      program_id: activeContext.program.id,
      tenant_id: tenantId,
    } : null

    localStorage.setItem('sap_user', JSON.stringify({
      id: opts.user.id,
      full_name: opts.user.full_name,
      email: opts.user.email,
      tenant_id: tenantId,
      roles: opts.user.roles,
    }))
    localStorage.setItem('sap_active_program', JSON.stringify(program))
    if (project) {
      localStorage.setItem('sap_active_project', JSON.stringify(project))
    } else {
      localStorage.removeItem('sap_active_project')
    }
    window.currentProgramId = program.id
    window.currentProjectId = project?.id || null
  }, payload)
}

export async function syncActiveContext(
  page: Page,
  context: ActiveProgramProjectContext,
  options: ActiveContextOptions = {},
) {
  const payload = _buildPayload(context, options)
  await page.waitForFunction(() => typeof window.App === 'object')
  await page.evaluate(async (browserPayload) => {
    const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
    const activeContext = browserPayload.context
    const opts = browserPayload.options
    const tenantId = activeContext.program.tenant_id || activeContext.project?.tenant_id || 1
    const program = {
      id: activeContext.program.id,
      name: activeContext.program.name,
      status: activeContext.program.status || 'active',
      project_type: activeContext.program.project_type || 'sap_activate',
      tenant_id: tenantId,
    }
    const project = activeContext.project ? {
      id: activeContext.project.id,
      name: activeContext.project.name,
      code: activeContext.project.code,
      program_id: activeContext.program.id,
      tenant_id: tenantId,
    } : null

    localStorage.setItem('sap_user', JSON.stringify({
      id: opts.user.id,
      full_name: opts.user.full_name,
      email: opts.user.email,
      tenant_id: tenantId,
      roles: opts.user.roles,
    }))

    if (opts.useAppSetters && typeof App.setActiveProgram === 'function') {
      App.setActiveProgram(program, { syncUrl: false, silent: true })
      await wait(250)
    } else {
      localStorage.setItem('sap_active_program', JSON.stringify(program))
    }

    if (project) {
      if (opts.useAppSetters && typeof App.setActiveProject === 'function') {
        App.setActiveProject(project, { syncUrl: false, silent: true })
        await wait(50)
      } else {
        localStorage.setItem('sap_active_project', JSON.stringify(project))
      }
    } else {
      localStorage.removeItem('sap_active_project')
    }

    window.currentProgramId = program.id
    window.currentProjectId = project?.id || null
    App.state = {
      programId: program.id,
      currentProgramId: program.id,
      projectId: project?.id || null,
      currentProjectId: project?.id || null,
    }
    if (typeof App.updateProgramBadge === 'function') App.updateProgramBadge()
    if (typeof App.updateSidebarState === 'function') App.updateSidebarState()
    if (typeof App.renderContextBanner === 'function') App.renderContextBanner()
  }, payload)

  if (payload.options.waitForProjectSync && payload.options.expectProjectId != null) {
    await page.waitForFunction((projectId) => {
      return typeof window.App === 'object'
        && typeof App.getActiveProject === 'function'
        && App.getActiveProject()?.id === projectId
    }, payload.options.expectProjectId)
  }
}

export async function openWithActiveContext(
  page: Page,
  context: ActiveProgramProjectContext,
  options: ActiveContextOptions = {},
) {
  await primeActiveContext(page, context, options)
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await syncActiveContext(page, context, options)
  if (options.route) {
    await page.evaluate((route) => { App.navigate(route) }, options.route)
  }
  await page.waitForLoadState('networkidle')
}

export async function expectAppReady(page: Page) {
  await expect.poll(async () => {
    return await page.evaluate(() => typeof App !== 'undefined' && Boolean(App.navigate))
  }).toBeTruthy()
}
