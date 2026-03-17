/**
 * E2E Flow 4: Data Factory — CRUD cycle for data objects.
 */
import { test, expect } from '@playwright/test'
import { createProgramContext } from './helpers/seed-factory'

let programId: number

test.beforeAll(async ({ request }) => {
  const context = await createProgramContext(request, {
    namePrefix: 'E2E DF Test',
    methodology: 'sap_activate',
    programData: {
      project_type: 'greenfield',
      sap_product: 'S/4HANA',
    },
  })
  programId = context.program.id
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
