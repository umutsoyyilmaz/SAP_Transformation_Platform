/**
 * E2E Flow 3: Explore Phase — IA and UX smoke
 */
import { test, expect, Page } from '@playwright/test'
import { expectAppReady, openWithActiveContext } from './helpers/active-context'
import { createProgramContext } from './helpers/seed-factory'

test('explore APIs for workshops and hierarchy stay reachable', async ({ request }) => {
  const res = await request.get('/api/v1/explore/workshops?project_id=1')
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  expect(Array.isArray(body.items || body)).toBeTruthy()

  const levelsRes = await request.get('/api/v1/explore/process-levels?project_id=1')
  expect(levelsRes.ok()).toBeTruthy()
})

test('explore ui exposes overview, outcomes, handoff, and workshops flow', async ({ page, request }) => {
  const context = await createProgramContext(request, {
    namePrefix: 'E2E Explore Smoke',
    methodology: 'sap_activate',
  })

  await openWithActiveContext(page, context as { program: any, project: any }, {
    user: {
      full_name: 'E2E Explore User',
      email: 'explore@example.com',
      roles: ['program_manager'],
    },
    useAppSetters: true,
  })
  await expect(page.locator('#sidebar [data-view="programs"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('#sidebar [data-view="explore-overview"]')).toBeVisible({ timeout: 20000 })

  await page.locator('#sidebar [data-view="explore-overview"]').click()
  await expect(page.locator('[data-testid="explore-overview-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('heading', { name: 'Explore Overview' })).toBeVisible()
  await expect(page.locator('[data-testid="explore-stage-nav"]')).toContainText('Scope & Process')
  await expect(page.locator('.explore-spotlight-grid')).toContainText('Handoff & Traceability')

  await page.evaluate(() => { App.navigate('explore-scope') })
  await expect(page.locator('[data-testid="explore-scope-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="explore-scope-governance-bridge"]')).toContainText('reviews the baseline')
  await expect(page.locator('[data-testid="explore-scope-page"]')).toContainText('Scope Change Queue')
  await expect(page.locator('[data-testid="explore-scope-page"]')).not.toContainText('Start from SAP Catalog')
  await expect(page.locator('[data-testid="explore-scope-page"]')).not.toContainText('Import L4')

  await page.evaluate(() => { App.navigate('explore-outcomes') })
  await expect(page.locator('[data-testid="explore-outcomes-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('heading', { name: 'Explore Outcomes' })).toBeVisible()
  await expect(page.locator('[data-testid="explore-outcomes-page"]')).toContainText('All Outcomes')
  await page.getByRole('button', { name: /Decisions \d+/ }).click()
  await expect(page.locator('[data-testid="explore-outcomes-decisions-workspace"]')).toBeVisible()
  await expect(page.locator('[data-testid="explore-outcomes-decisions-workspace"]')).toContainText('Decisions')

  await page.evaluate(() => { App.navigate('explore-traceability') })
  await expect(page.locator('[data-testid="explore-traceability-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('heading', { name: 'Handoff & Traceability' })).toBeVisible()
  await expect(page.locator('.explore-trace-table')).toContainText('Requirement Trace Matrix')

  await page.evaluate(() => { App.navigate('explore-workshops') })
  await expect(page.locator('[data-testid="explore-workshops-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('heading', { name: 'Workshop Hub' })).toBeVisible()
  await expect(page.locator('[data-testid="explore-workshops-page"]')).toContainText('Plan, run, and close Explore sessions')
})

test('discover ui exposes cockpit workspaces and legacy timeline/raci routes', async ({ page, request }) => {
  const context = await createProgramContext(request, {
    namePrefix: 'E2E Explore Smoke',
    methodology: 'sap_activate',
  })

  await openWithActiveContext(page, context as { program: any, project: any }, {
    user: {
      full_name: 'E2E Explore User',
      email: 'explore@example.com',
      roles: ['program_manager'],
    },
    useAppSetters: true,
  })
  await expectAppReady(page)

  await page.locator('#sidebar [data-view="discover"]').click()
  await expect(page.locator('[data-testid="discover-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.getByRole('heading', { name: 'Discover Phase' })).toBeVisible()
  await expect(page.locator('[data-testid="discover-overview-workspace"]')).toBeVisible()
  await expect(page.locator('[data-testid="discover-stage-nav"]')).toContainText('Project Charter')
  await expect(page.locator('[data-testid="discover-stage-nav"]')).toContainText('RACI')

  await page.locator('[data-workspace="charter"]').click()
  await expect(page.locator('[data-testid="discover-charter-workspace"]')).toBeVisible()
  await expect(page.locator('[data-testid="discover-charter-workspace"]')).toContainText('Project Charter')

  await page.locator('[data-workspace="landscape"]').click()
  await expect(page.locator('[data-testid="discover-landscape-workspace"]')).toBeVisible()
  await expect(page.locator('[data-testid="discover-landscape-workspace"]')).toContainText('System Landscape')

  await page.locator('[data-workspace="scope"]').click()
  await expect(page.locator('[data-testid="discover-scope-workspace"]')).toBeVisible()
  await expect(page.locator('[data-testid="discover-scope-workspace"]')).toContainText('Scope Assessment')

  await page.evaluate(() => { App.navigate('timeline') })
  await expect(page.locator('[data-testid="discover-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="discover-timeline-workspace"]')).toBeVisible()
  await expect(page.locator('[data-testid="discover-timeline-workspace"]')).toContainText('Phase Timeline')

  await page.evaluate(() => { App.navigate('raci') })
  await expect(page.locator('[data-testid="discover-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="discover-raci-workspace"]')).toBeVisible()
  await expect(page.locator('[data-testid="discover-raci-workspace"]')).toContainText('Responsibility Grid')
})
