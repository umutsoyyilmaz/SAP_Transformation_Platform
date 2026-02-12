/**
 * E2E Flow 1: Health check — verify the server responds.
 */
import { test, expect } from '@playwright/test'

test('health endpoint returns ok', async ({ request }) => {
  const res = await request.get('/api/v1/health')
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  expect(body.status).toBe('ok')
})

test('SPA index loads', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/SAP/)
})
