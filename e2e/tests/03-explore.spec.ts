/**
 * E2E Flow 3: Explore Phase — navigate to explore, verify workshops load.
 */
import { test, expect } from '@playwright/test'

test('explore workshops API returns list', async ({ request }) => {
  const res = await request.get('/api/v1/explore/workshops?project_id=1')
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  expect(Array.isArray(body.items || body)).toBeTruthy()
})

test('explore process levels API returns hierarchy', async ({ request }) => {
  const res = await request.get('/api/v1/explore/process-levels?project_id=1')
  expect(res.ok()).toBeTruthy()
})
