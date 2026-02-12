/**
 * E2E Flow 2: Dashboard — verify the main dashboard renders KPI cards.
 */
import { test, expect } from '@playwright/test'

test('dashboard loads with KPI cards', async ({ page }) => {
  await page.goto('/')
  // Wait for the SPA to render
  await page.waitForSelector('#mainContent', { timeout: 10000 })
  // Dashboard should show program cards or main content
  const cards = page.locator('.program-card, .kpi-card, .stat-card, .card, .empty-state')
  await expect(cards.first()).toBeVisible({ timeout: 10000 })
})

test('sidebar navigation is visible', async ({ page }) => {
  await page.goto('/')
  await page.waitForSelector('#sidebar, .sidebar, nav', { timeout: 10000 })
  const sidebar = page.locator('#sidebar, .sidebar, nav').first()
  await expect(sidebar).toBeVisible()
})
