/**
 * E2E Flow 16: Cutover / Integration project-owned owner scope smoke
 */
import { test, expect, APIRequestContext } from '@playwright/test'
import { openWithActiveContext } from './helpers/active-context'
import { createDownstreamScopeSeedContext } from './helpers/program-setup-seed'

async function createDownstreamScopeContext(request: APIRequestContext) {
  return createDownstreamScopeSeedContext(request)
}

test('integration interface form limits assignee options to the active project', async ({ page, request }) => {
  const context = await createDownstreamScopeContext(request)
  const interfaceName = `Scoped Interface ${Date.now()}`

  await openWithActiveContext(page, context as { program: any, project: any }, {
    user: {
      full_name: 'E2E Downstream Scope User',
      email: 'downstream-scope@example.com',
      roles: ['program_manager'],
    },
  })

  await page.evaluate(() => { App.navigate('integration') })
  await expect(page.locator('[data-testid="integration-page"]')).toBeVisible({ timeout: 20000 })
  await page.locator('[data-testid="integration-page"]').getByRole('button', { name: '+ New Interface' }).click()
  await expect(page.locator('[data-testid="integration-interface-modal"]')).toBeVisible()
  await expect(page.locator('#ifAssigned')).toContainText(context.activeMemberName)
  await expect(page.locator('#ifAssigned')).not.toContainText(context.foreignMemberName)
  await expect(page.locator('#ifWave')).toContainText(context.activeWaveName)
  await expect(page.locator('#ifWave')).not.toContainText(context.foreignWaveName)

  await page.locator('#ifName').fill(interfaceName)
  await page.locator('#ifAssigned').selectOption(String(context.activeMember.id))
  await page.locator('#ifWave').selectOption(String(context.activeWave.id))
  await page.getByRole('button', { name: 'Create' }).click()

  await expect(page.locator('[data-testid="integration-content"]')).toContainText(interfaceName, { timeout: 20000 })

  const interfaceRow = page.locator('[data-testid="integration-content"] tbody tr').filter({ hasText: interfaceName })
  await interfaceRow.click()
  await page.getByRole('button', { name: 'Delete' }).click()
  await expect(page.locator('[data-testid="integration-confirm-modal"]')).toContainText('Delete this interface')
  await page.locator('[data-testid="integration-confirm-cancel"]').click()
  await expect(page.locator('[data-testid="integration-content"]')).toContainText(interfaceName)

  await interfaceRow.click()
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.locator('[data-testid="integration-confirm-submit"]').click()
  await expect(page.locator('[data-testid="integration-content"]')).not.toContainText(interfaceName)
})

test('cutover plan form limits manager options to the active project and creates a scoped plan', async ({ page, request }) => {
  const context = await createDownstreamScopeContext(request)
  const planName = `Scoped Cutover ${Date.now()}`

  await openWithActiveContext(page, context as { program: any, project: any }, {
    user: {
      full_name: 'E2E Downstream Scope User',
      email: 'downstream-scope@example.com',
      roles: ['program_manager'],
    },
  })

  await page.evaluate(() => { App.navigate('cutover') })
  await expect(page.locator('[data-testid="cutover-page"]')).toBeVisible({ timeout: 20000 })
  await page.locator('[data-testid="cutover-page"]').getByRole('button', { name: '+ New Plan' }).click()
  await expect(page.locator('#cutMgr')).toBeVisible()
  await expect(page.locator('#cutMgr')).toContainText(context.activeMemberName)
  await expect(page.locator('#cutMgr')).not.toContainText(context.foreignMemberName)

  await page.locator('input[name="name"]').fill(planName)
  await page.locator('#cutMgr').selectOption(String(context.activeMember.id))
  await page.getByRole('button', { name: 'Save' }).click()

  await expect(page.locator('[data-testid="cutover-content"]')).toContainText(planName, { timeout: 20000 })

  await page.locator('[data-testid="cutover-delete-plan-trigger"]').click()
  await expect(page.locator('[data-testid="cutover-confirm-modal"]')).toContainText('Delete this cutover plan')
  await page.locator('[data-testid="cutover-confirm-cancel"]').click()
  await expect(page.locator('[data-testid="cutover-content"]')).toContainText(planName)

  await page.locator('[data-testid="cutover-delete-plan-trigger"]').click()
  await page.locator('[data-testid="cutover-confirm-submit"]').click()
  await expect(page.locator('[data-testid="cutover-content"]')).not.toContainText(planName)
})
