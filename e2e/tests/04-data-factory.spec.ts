/**
 * E2E Flow 4: Data Factory — CRUD cycle for data objects.
 */
import { test, expect } from '@playwright/test'

let programId: number

test.beforeAll(async ({ request }) => {
  const res = await request.post('/api/v1/programs', {
    data: {
      name: 'E2E DF Test',
      project_type: 'greenfield',
      methodology: 'sap_activate',
      sap_product: 'S/4HANA',
    },
  })
  const body = await res.json()
  programId = body.id
})

test('create data object', async ({ request }) => {
  const res = await request.post('/api/v1/data-factory/objects', {
    data: {
      program_id: programId,
      name: 'E2E Customer Master',
      source_system: 'SAP ECC',
    },
  })
  expect(res.status()).toBe(201)
  const body = await res.json()
  expect(body.name).toBe('E2E Customer Master')
})

test('list data objects', async ({ request }) => {
  const res = await request.get(`/api/v1/data-factory/objects?program_id=${programId}`)
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  expect(body.total).toBeGreaterThanOrEqual(1)
})

test('quality score dashboard', async ({ request }) => {
  const res = await request.get(`/api/v1/data-factory/quality-score?program_id=${programId}`)
  expect(res.ok()).toBeTruthy()
})
