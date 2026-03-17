import { test, expect, APIRequestContext } from '@playwright/test'
import { openWithActiveContext } from './helpers/active-context'
import { createProgramContext } from './helpers/seed-factory'

async function createBacklogContext(request: APIRequestContext) {
  const { program, project } = await createProgramContext(request, {
    namePrefix: 'E2E Backlog Move',
    methodology: 'sap_activate',
  })

  const itemRes = await request.post(`/api/v1/programs/${program.id}/backlog`, {
    data: {
      project_id: project.id,
      title: 'Live Move Regression Item',
      code: 'ENH-E2E-001',
      wricef_type: 'enhancement',
      module: 'MM',
      priority: 'high',
      status: 'new',
    },
  })
  expect(itemRes.ok()).toBeTruthy()
  const item = await itemRes.json()

  return {
    program,
    project,
    item,
  }
}

test('backlog quick move updates kanban columns without full refresh', async ({ page, request }) => {
  const context = await createBacklogContext(request)

  await openWithActiveContext(page, context, {
    route: 'backlog',
    user: {
      full_name: 'E2E Backlog User',
      email: 'backlog-e2e@example.com',
      roles: ['program_manager'],
    },
  })
  await expect(page.locator('#backlogContent')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('.kanban-column[data-status="new"] .kanban-card')).toContainText('Live Move Regression Item')

  await page.evaluate(async (itemId) => {
    await BacklogView.openDetail(itemId)
  }, context.item.id)

  await expect(page.locator('#quickMoveStatus')).toBeVisible({ timeout: 20000 })
  await page.locator('#quickMoveStatus').selectOption('design')
  await page.locator('.backlog-quick__move-cta').click()

  await expect(page.locator(`.kanban-column[data-status="design"] .kanban-card[data-id="${context.item.id}"]`)).toBeVisible({ timeout: 20000 })
  await expect(page.locator(`.kanban-column[data-status="new"] .kanban-card[data-id="${context.item.id}"]`)).toHaveCount(0)
})
