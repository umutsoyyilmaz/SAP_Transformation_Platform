/**
 * E2E Flow 2: Workspace shell — dashboard and executive cockpit
 */
import { test, expect } from '@playwright/test'
import { openWithActiveContext } from './helpers/active-context'
import { createProgramContext } from './helpers/seed-factory'

test('workspace navigation exposes dashboard and executive cockpit shells', async ({ page, request }) => {
  const context = await createProgramContext(request, {
    namePrefix: 'E2E Workspace',
    methodology: 'sap_activate',
  })

  await openWithActiveContext(page, context, {
    user: {
      full_name: 'E2E Workspace User',
      email: 'workspace@example.com',
      roles: ['program_manager'],
    },
  })
  await expect(page.locator('#sidebar [data-view="dashboard"]')).toBeVisible({ timeout: 20000 })

  await page.locator('#sidebar [data-view="dashboard"]').click()
  await expect(page.locator('[data-testid="workspace-dashboard-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="workspace-nav"]')).toContainText('Executive Cockpit')
  await expect(page.locator('[data-testid="workspace-dashboard-grid"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="workspace-dashboard-focus"]')).toContainText('Operational Focus')

  await page.locator('[data-testid="workspace-nav"] [data-workspace-view="executive-cockpit"]').click()
  await expect(page.locator('[data-testid="workspace-executive-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="workspace-executive-summary"]')).toContainText('Overall Status')
  await expect(page.locator('[data-testid="workspace-executive-actions"]')).toContainText('Operational Dashboard')
  await expect(page.locator('#sidebar [data-view="dashboard"]')).toHaveClass(/active/)
})
