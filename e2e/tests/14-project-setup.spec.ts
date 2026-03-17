/**
 * E2E Flow 14: Project Setup bootstrap cockpit
 */
import { test, expect, APIRequestContext } from '@playwright/test'
import { openWithActiveContext } from './helpers/active-context'
import { createProgramWorkstream, createProjectSetupSeedContext } from './helpers/program-setup-seed'

async function createProjectSetupContext(request: APIRequestContext) {
  const { program, project } = await createProjectSetupSeedContext(request)
  return { program, project }
}

test('project setup manages project-owned workstreams and team workstream binding', async ({ page, request }) => {
  const context = await createProjectSetupContext(request)
  const workstreamName = `Finance Stream ${Date.now()}`
  const memberName = `Owner ${Date.now()}`
  await createProgramWorkstream(request, context.program.id, {
    name: workstreamName,
    project_id: context.project.id,
  })

  await openWithActiveContext(page, context as { program: any, project: any }, {
    user: {
      full_name: 'E2E Project Setup User',
      email: 'project-setup@example.com',
      roles: ['program_manager'],
    },
  })

  await page.locator('#sidebar [data-view="project-setup"]').click()
  await expect(page.locator('[data-testid="project-setup-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="project-setup-context"]')).toContainText(context.project.name)
  await expect(page.locator('[data-testid="project-setup-profile"]')).toContainText('Methodology')

  await page.locator('[data-testid="project-setup-tabs"] [data-setup-tab="workstreams"]').click()
  await expect(page.locator('[data-testid="project-setup-workstreams-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="project-setup-workstreams"]')).toContainText(workstreamName)

  await page.locator('[data-testid="project-setup-tabs"] [data-setup-tab="team"]').click()
  await expect(page.getByRole('heading', { name: 'Project Team' })).toBeVisible({ timeout: 20000 })
  await page.getByRole('button', { name: '+ Add Member' }).click()
  await expect(page.locator('#tm_workstream_id')).toBeVisible()
  await expect(page.locator('#tm_workstream_id')).toContainText(workstreamName)
  await page.locator('#tm_name').fill(memberName)
  await page.locator('#tm_workstream_id').selectOption({ label: workstreamName })
  await page.getByRole('button', { name: '💾 Save' }).click()
  await expect(page.locator('[data-testid="project-setup-team-table"]')).toContainText(memberName)
  await expect(page.locator('[data-testid="project-setup-team-table"]')).toContainText(workstreamName)

  await page.locator('[data-testid="project-setup-tabs"] [data-setup-tab="workstreams"]').click()
  const workstreamRow = page.locator('[data-testid="project-setup-workstreams"] tbody tr').filter({ hasText: workstreamName })
  await workstreamRow.getByTitle('Delete').click()
  await expect(page.locator('[data-testid="project-setup-confirm-modal"]')).toContainText(workstreamName)
  await page.locator('[data-testid="project-setup-confirm-cancel"]').click()
  await expect(workstreamRow).toContainText(workstreamName)

  await workstreamRow.getByTitle('Delete').click()
  await page.locator('[data-testid="project-setup-confirm-submit"]').click()
  await expect(page.locator('[data-testid="project-setup-workstreams"]')).not.toContainText(workstreamName)

  await page.locator('[data-testid="project-setup-tabs"] [data-setup-tab="team"]').click()
  const memberRow = page.locator('[data-testid="project-setup-team-table"] tbody tr').filter({ hasText: memberName })
  await expect(memberRow).toContainText(memberName)
  await expect(memberRow).not.toContainText(workstreamName)

  await page.locator('[data-testid="project-setup-tabs"] [data-setup-tab="committees"]').click()
  await expect(page.locator('[data-testid="project-setup-committees-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="project-setup-committees"]')).toContainText('No committees defined')
})

test('project setup hierarchy requests use active project scope', async ({ page, request }) => {
  const context = await createProjectSetupContext(request)

  await openWithActiveContext(page, context as { program: any, project: any }, {
    user: {
      full_name: 'E2E Project Setup User',
      email: 'project-setup@example.com',
      roles: ['program_manager'],
    },
  })

  await page.locator('#sidebar [data-view="project-setup"]').click()
  await expect(page.locator('[data-testid="project-setup-page"]')).toBeVisible({ timeout: 20000 })
  const scopeHierarchyTab = page.locator('[data-testid="project-setup-tabs"] [data-setup-tab="scope-hierarchy"]')
  await expect(scopeHierarchyTab).toBeVisible({ timeout: 20000 })
  await scopeHierarchyTab.scrollIntoViewIfNeeded()

  const treeRequestPromise = page.waitForRequest((req) => {
    const url = new URL(req.url())
    return url.pathname.endsWith('/api/v1/explore/process-levels')
      && url.searchParams.get('project_id') === String(context.project.id)
      && url.searchParams.get('level') === null
  })

  await scopeHierarchyTab.click()
  const treeRequest = await treeRequestPromise
  const requestUrl = new URL(treeRequest.url())
  expect(requestUrl.searchParams.get('project_id')).toBe(String(context.project.id))
  expect(requestUrl.searchParams.get('program_id')).toBeNull()
  expect(requestUrl.searchParams.get('level')).toBeNull()
})
