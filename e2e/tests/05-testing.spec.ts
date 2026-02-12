/**
 * E2E Flow 5: Test Management — verify test plans and cycles APIs.
 */
import { test, expect } from '@playwright/test'

test('test plans API returns list', async ({ request }) => {
  const res = await request.get('/api/v1/programs/1/testing/plans')
  expect(res.ok()).toBeTruthy()
})

test('test cycles API returns list', async ({ request }) => {
  // Cycles are nested under plans — get first plan then its cycles
  const planRes = await request.get('/api/v1/programs/1/testing/plans')
  const plans = (await planRes.json()).items || await planRes.json()
  if (plans.length > 0) {
    const res = await request.get(`/api/v1/testing/plans/${plans[0].id}/cycles`)
    expect(res.ok()).toBeTruthy()
  }
})

test('defects API returns list', async ({ request }) => {
  const res = await request.get('/api/v1/programs/1/testing/defects')
  expect(res.ok()).toBeTruthy()
})
