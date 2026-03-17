/**
 * E2E Flow 15: Program portfolio to Project Setup launchpad
 */
import { test, expect, APIRequestContext } from '@playwright/test'
import { openWithActiveContext } from './helpers/active-context'
import { createProgramLaunchpadSeedContext } from './helpers/program-setup-seed'

async function createProgramLaunchpadContext(request: APIRequestContext) {
  const { program, project } = await createProgramLaunchpadSeedContext(request)
  return { program, project }
}

test('program projects tab acts as the launchpad into project setup', async ({ page, request }) => {
  const context = await createProgramLaunchpadContext(request)

  await openWithActiveContext(page, context as { program: any, project: any }, {
    user: {
      full_name: 'E2E Program User',
      email: 'program@example.com',
      roles: ['program_manager'],
    },
  })

  await page.locator('#sidebar [data-view="programs"]').click()
  await page.locator('.program-card').filter({ hasText: context.program.name }).first().click()
  await expect(page.locator('[data-testid="program-detail-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="program-detail-page"]')).toContainText('Execution setup such as phases, workstreams, team, and committees lives inside each project.')

  await page.locator('[data-testid="program-detail-tabs"] [data-tab="projects"]').click()
  await expect(page.locator('[data-testid="program-projects-tab"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="program-projects-tab"]')).toContainText('Project Setup')
  await expect(page.locator('[data-testid="program-projects-table"]')).toContainText(context.project.name)

  await page.getByRole('button', { name: /Open|Setup/ }).first().click()
  await expect(page.locator('[data-testid="project-setup-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="project-setup-context"]')).toContainText(context.project.name)
})

test('my projects uses project setup as the canonical launch target', async ({ page, request }) => {
  const context = await createProgramLaunchpadContext(request)

  await openWithActiveContext(page, context as { program: any, project: any }, {
    user: {
      full_name: 'E2E Program User',
      email: 'program@example.com',
      roles: ['program_manager'],
    },
  })

  await page.locator('#sidebar [data-view="my-projects"]').click()
  await expect(page.locator('.pg-view-title')).toContainText('My Projects', { timeout: 20000 })
  await expect(page.locator('#mainContent')).toContainText('Project Setup is the canonical bootstrap cockpit')
  await expect(page.locator('#mainContent')).toContainText(context.project.name)

  const projectCard = page.locator('.program-card').filter({ hasText: context.project.name }).first()
  await expect(projectCard).toBeVisible({ timeout: 20000 })
  await projectCard.getByRole('button', { name: 'Open Setup' }).click()
  await expect(page.locator('[data-testid="project-setup-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="project-setup-context"]')).toContainText(context.project.name)
})
