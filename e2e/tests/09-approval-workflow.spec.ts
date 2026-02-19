/**
 * E2E Flow 9: Approval Workflow — F3 coverage.
 *
 * Tests the approval workflow CRUD, submit, decide, and query APIs.
 */
import { test, expect } from '@playwright/test'

const API = '/api/v1'

let programId: number
let workflowId: number
let testCaseId: number

test.describe.serial('Approval Workflow (F3)', () => {
  test('create program for approval tests', async ({ request }) => {
    const res = await request.post(`${API}/programs`, {
      data: { name: 'E2E Approval Program', methodology: 'agile' },
    })
    expect(res.ok()).toBeTruthy()
    programId = (await res.json()).id
  })

  test('create approval workflow', async ({ request }) => {
    const res = await request.post(`${API}/programs/${programId}/approval-workflows`, {
      data: {
        name: 'TC 2-Stage Review',
        entity_type: 'test_case',
        stages: [
          { stage: 1, role: 'Reviewer', required: true },
          { stage: 2, role: 'QA Lead', required: true },
        ],
      },
    })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    workflowId = body.id
    expect(body.name).toBe('TC 2-Stage Review')
    expect(body.stages).toHaveLength(2)
  })

  test('list workflows', async ({ request }) => {
    const res = await request.get(`${API}/programs/${programId}/approval-workflows`)
    expect(res.ok()).toBeTruthy()
    const items = await res.json()
    expect(items.length).toBeGreaterThanOrEqual(1)
  })

  test('update workflow', async ({ request }) => {
    const res = await request.put(`${API}/approval-workflows/${workflowId}`, {
      data: { name: 'TC 2-Stage Review (Updated)' },
    })
    expect(res.ok()).toBeTruthy()
    expect((await res.json()).name).toBe('TC 2-Stage Review (Updated)')
  })

  test('create test case for approval flow', async ({ request }) => {
    const res = await request.post(`${API}/programs/${programId}/testing/catalog`, {
      data: { title: 'E2E Approval TC', test_type: 'Manual', test_layer: 'regression' },
    })
    expect(res.ok()).toBeTruthy()
    testCaseId = (await res.json()).id
  })

  test('submit entity for approval', async ({ request }) => {
    const res = await request.post(`${API}/approvals/submit`, {
      data: { entity_type: 'test_case', entity_id: testCaseId },
    })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.submitted).toBe(true)
    expect(body.records).toHaveLength(2)
  })

  test('pending approvals returns records', async ({ request }) => {
    const res = await request.get(`${API}/approvals/pending?program_id=${programId}`)
    expect(res.ok()).toBeTruthy()
    const items = await res.json()
    expect(items.length).toBeGreaterThanOrEqual(2)
  })

  test('entity approval status is pending', async ({ request }) => {
    const res = await request.get(`${API}/test_case/${testCaseId}/approval-status`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.status).toBe('pending')
    expect(body.records).toHaveLength(2)
  })

  test('approve stage 1', async ({ request }) => {
    const pending = await (await request.get(`${API}/approvals/pending?program_id=${programId}`)).json()
    const stage1 = pending.find((r: any) => r.stage === 1 && r.entity_id === testCaseId)
    expect(stage1).toBeDefined()

    const res = await request.post(`${API}/approvals/${stage1.id}/decide`, {
      data: { decision: 'approved', comment: 'LGTM' },
    })
    expect(res.ok()).toBeTruthy()
    expect((await res.json()).status).toBe('approved')
  })

  test('approve stage 2 → entity becomes approved', async ({ request }) => {
    const pending = await (await request.get(`${API}/approvals/pending?program_id=${programId}`)).json()
    const stage2 = pending.find((r: any) => r.stage === 2 && r.entity_id === testCaseId)
    expect(stage2).toBeDefined()

    const res = await request.post(`${API}/approvals/${stage2.id}/decide`, {
      data: { decision: 'approved' },
    })
    expect(res.ok()).toBeTruthy()

    // Entity should now be approved
    const status = await (await request.get(`${API}/test_case/${testCaseId}/approval-status`)).json()
    expect(status.status).toBe('approved')
  })

  test('delete workflow', async ({ request }) => {
    const res = await request.delete(`${API}/approval-workflows/${workflowId}`)
    expect(res.ok()).toBeTruthy()
    expect((await res.json()).deleted).toBe(true)
  })
})
