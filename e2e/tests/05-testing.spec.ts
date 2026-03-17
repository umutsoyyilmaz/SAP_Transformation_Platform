/**
 * E2E Flow 5: Test Management — verify test plans and cycles APIs.
 */
import { test, expect } from '@playwright/test'
import { createProgramContext } from './helpers/seed-factory'

let programId: number
let planId: number

test.beforeAll(async ({ request }) => {
  const context = await createProgramContext(request, {
    namePrefix: 'E2E Testing API',
    methodology: 'sap_activate',
  })
  programId = context.program.id

  const planRes = await request.post(`/api/v1/programs/${programId}/testing/plans`, {
    data: {
      name: 'E2E API Plan',
      plan_type: 'sit',
    },
  })
  expect(planRes.ok()).toBeTruthy()
  planId = (await planRes.json()).id

  const cycleRes = await request.post(`/api/v1/testing/plans/${planId}/cycles`, {
    data: {
      name: 'E2E API Cycle',
      cycle_type: 'sit',
    },
  })
  expect(cycleRes.ok()).toBeTruthy()

  const defectRes = await request.post(`/api/v1/programs/${programId}/testing/defects`, {
    data: {
      title: 'E2E API Defect',
      severity: 'P2',
      status: 'open',
    },
  })
  expect(defectRes.ok()).toBeTruthy()
})

test('test plans API returns list', async ({ request }) => {
  const res = await request.get(`/api/v1/programs/${programId}/testing/plans`)
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const items = body.items || body
  expect(Array.isArray(items)).toBeTruthy()
  expect(items.some((item: any) => item.id === planId)).toBeTruthy()
})

test('test cycles API returns list', async ({ request }) => {
  const res = await request.get(`/api/v1/testing/plans/${planId}/cycles`)
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const items = body.items || body
  expect(Array.isArray(items)).toBeTruthy()
  expect(items.length).toBeGreaterThanOrEqual(1)
})

test('defects API returns list', async ({ request }) => {
  const res = await request.get(`/api/v1/programs/${programId}/testing/defects`)
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const items = body.items || body
  expect(Array.isArray(items)).toBeTruthy()
  expect(items.length).toBeGreaterThanOrEqual(1)
})
