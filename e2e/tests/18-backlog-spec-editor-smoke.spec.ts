import { APIRequestContext, expect, test } from '@playwright/test'

import { expectAppReady, openWithActiveContext } from './helpers/active-context'
import { createProgramContext } from './helpers/seed-factory'

async function createBacklogSpecContext(request: APIRequestContext) {
  const suffix = Date.now()
  const { program, project } = await createProgramContext(request, {
    namePrefix: 'E2E Backlog Spec Editor',
    methodology: 'sap_activate',
  })

  const itemRes = await request.post(`/api/v1/programs/${program.id}/backlog`, {
    data: {
      project_id: project.id,
      title: `Spec Editor Persistence ${suffix}`,
      code: `INT-E2E-${suffix}`,
      wricef_type: 'interface',
      module: 'SD',
      priority: 'high',
      status: 'design',
    },
  })
  expect(itemRes.ok()).toBeTruthy()
  const item = await itemRes.json()

  const generateRes = await request.post(`/api/v1/backlog/${item.id}/generate-specs`)
  expect(generateRes.ok()).toBeTruthy()

  const loadDetail = async () => {
    const detailRes = await request.get(`/api/v1/backlog/${item.id}?include_specs=true`)
    expect(detailRes.ok()).toBeTruthy()
    return detailRes.json()
  }

  let detail = await loadDetail()

  if (!detail.functional_spec?.technical_spec?.id && detail.functional_spec?.id) {
    const retryGenerateRes = await request.post(`/api/v1/backlog/${item.id}/generate-specs`)
    expect([201, 409]).toContain(retryGenerateRes.status())
    detail = await loadDetail()
  }

  if (!detail.functional_spec?.technical_spec?.id && detail.functional_spec?.id) {
    const technicalContent = [
      '# Technical Specification',
      `## ${detail.code} — ${detail.title}`,
      '',
      '| Field | Value |',
      '|---|---|',
      '| Type | Interface (I) |',
      '| Module | SD |',
      '',
      '---',
      '',
      '## 1. Technical Document Control',
      '',
      '| Item | Value |',
      '|---|---|',
      `| Document ID | ${detail.code} |`,
      '| Version | 2.0 |',
      '| Status | Draft |',
      '',
      '## 2. Solution Overview & Architecture',
      '',
      '**Technical Purpose:**',
      'Initial purpose',
      '',
      '**Landscape / Components:**',
      '- Source system(s):',
      '- Middleware / Runtime:',
      '',
      '## 3. Technical Object Inventory',
      '',
      '| Object Type | Object Name | Package / Namespace | Description | New / Change |',
      '|---|---|---|---|---|',
      '| ABAP Class / Program | | ZPKG | | New |',
      '',
      '## 4. Open Points',
      '',
      '| # | Description | Owner | Due Date | Status |',
      '|---|---|---|---|---|',
      '| 1 | | | | Open |',
    ].join('\n')

    const createTsRes = await request.post(`/api/v1/functional-specs/${detail.functional_spec.id}/technical-spec`, {
      data: {
        title: `TS — ${detail.code}`,
        content: technicalContent,
        version: '0.1',
        status: 'draft',
      },
    })
    expect(createTsRes.ok()).toBeTruthy()
    detail = await loadDetail()
  }

  expect(detail.functional_spec?.technical_spec?.id).toBeTruthy()

  return {
    program,
    project,
    item: detail,
    ts: detail.functional_spec.technical_spec,
  }
}

test('technical spec editor persists structured content after save and reload', async ({ page, request }) => {
  const context = await createBacklogSpecContext(request)
  const purposeText = `Persisted technical purpose ${Date.now()}`
  const componentText = `Source system: S/4HANA\nMiddleware / Runtime: SAP Integration Suite`
  const objectName = `ZCL_E2E_${Date.now()}`
  const objectDescription = 'Maps outbound payload for order replication'

  await openWithActiveContext(page, context, {
    route: 'backlog',
    user: {
      full_name: 'E2E Spec User',
      email: 'backlog-spec-e2e@example.com',
      roles: ['program_manager'],
    },
  })

  const openTechnicalSpecEditor = async () => {
    await page.evaluate(async (itemId) => {
      await BacklogView.openDetail(itemId)
    }, context.item.id)

    await expect(page.getByRole('button', { name: 'Open Full Detail' })).toBeVisible({ timeout: 20000 })
    await page.getByRole('button', { name: 'Open Full Detail' }).click()
    await expect(page.getByRole('button', { name: '📑 Specs (FS/TS)' })).toBeVisible({ timeout: 20000 })
    await page.getByRole('button', { name: '📑 Specs (FS/TS)' }).click()
    await expect(page.locator('.backlog-detail-card')).toHaveCount(2, { timeout: 20000 })
    await page.locator('.backlog-detail-card').nth(1).getByRole('button', { name: /Edit/ }).click()
    await expect(page.locator('#specEditorPanel')).toBeVisible({ timeout: 20000 })
  }

  await expect(page.locator('#backlogContent')).toBeVisible({ timeout: 20000 })
  await openTechnicalSpecEditor()

  await page.locator('#specEditorNav .backlog-spec-editor__nav-item').filter({ hasText: 'Solution Overview & Architecture' }).click()
  await expect(page.locator('#specEditorPanel')).toContainText('Solution Overview & Architecture')
  await page.locator('#specEditorPanel textarea').nth(0).fill(purposeText)
  await page.locator('#specEditorPanel textarea').nth(1).fill(componentText)

  await page.locator('#specEditorNav .backlog-spec-editor__nav-item').filter({ hasText: 'Technical Object Inventory' }).click()
  await expect(page.locator('#specEditorPanel')).toContainText('Technical Object Inventory')
  const firstInventoryRow = page.locator('#specEditorPanel .backlog-spec-editor__entry-card').first()
  await firstInventoryRow.locator('input').nth(1).fill(objectName)
  await firstInventoryRow.locator('input').nth(3).fill(objectDescription)

  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.locator('#specEditorPreview')).toContainText(purposeText)
  await expect(page.locator('#specEditorPreview')).toContainText(objectName)

  await page.reload({ waitUntil: 'domcontentloaded' })
  await expectAppReady(page)
  await page.evaluate(() => { App.navigate('backlog') })
  await expect(page.locator('#backlogContent')).toBeVisible({ timeout: 20000 })
  await openTechnicalSpecEditor()

  await page.locator('#specEditorNav .backlog-spec-editor__nav-item').filter({ hasText: 'Solution Overview & Architecture' }).click()
  await expect(page.locator('#specEditorPanel textarea').nth(0)).toHaveValue(purposeText)
  await expect(page.locator('#specEditorPanel textarea').nth(1)).toHaveValue(componentText)

  await page.locator('#specEditorNav .backlog-spec-editor__nav-item').filter({ hasText: 'Technical Object Inventory' }).click()
  const persistedInventoryRow = page.locator('#specEditorPanel .backlog-spec-editor__entry-card').first()
  await expect(persistedInventoryRow.locator('input').nth(1)).toHaveValue(objectName)
  await expect(persistedInventoryRow.locator('input').nth(3)).toHaveValue(objectDescription)
})
