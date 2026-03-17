/**
 * E2E Flow 9: Approval Workflow — F3 coverage.
 *
 * Tests the approval workflow CRUD, submit, decide, and query APIs.
 */
import { test, expect } from '@playwright/test'
import {
  createApprovalProgramContext,
  createApprovalTestCase,
  createApprovalWorkflow,
  decideApproval,
  deleteApprovalWorkflow,
  findPendingApprovalStage,
  getTestCaseApprovalStatus,
  listApprovalWorkflows,
  listPendingApprovals,
  submitEntityForApproval,
  updateApprovalWorkflow,
} from './helpers/approval-seed'

let programId: number
let workflowId: number
let testCaseId: number

test.describe.serial('Approval Workflow (F3)', () => {
  test('create program for approval tests', async ({ request }) => {
    const context = await createApprovalProgramContext(request, 'E2E Approval Program')
    programId = context.program.id
  })

  test('create approval workflow', async ({ request }) => {
    const body = await createApprovalWorkflow(request, programId)
    workflowId = body.id
    expect(body.name).toBe('TC 2-Stage Review')
    expect(body.stages).toHaveLength(2)
  })

  test('list workflows', async ({ request }) => {
    const items = await listApprovalWorkflows(request, programId)
    expect(items.length).toBeGreaterThanOrEqual(1)
  })

  test('update workflow', async ({ request }) => {
    const workflow = await updateApprovalWorkflow(request, workflowId, {
      name: 'TC 2-Stage Review (Updated)',
    })
    expect(workflow.name).toBe('TC 2-Stage Review (Updated)')
  })

  test('create test case for approval flow', async ({ request }) => {
    const testCase = await createApprovalTestCase(request, programId)
    testCaseId = testCase.id
  })

  test('submit entity for approval', async ({ request }) => {
    const body = await submitEntityForApproval(request, 'test_case', testCaseId)
    expect(body.submitted).toBe(true)
    expect(body.records).toHaveLength(2)
  })

  test('pending approvals returns records', async ({ request }) => {
    const items = await listPendingApprovals(request, programId)
    expect(items.length).toBeGreaterThanOrEqual(2)
  })

  test('entity approval status is pending', async ({ request }) => {
    const body = await getTestCaseApprovalStatus(request, testCaseId)
    expect(body.status).toBe('pending')
    expect(body.records).toHaveLength(2)
  })

  test('approve stage 1', async ({ request }) => {
    const stage1 = await findPendingApprovalStage(request, programId, testCaseId, 1)
    const approval = await decideApproval(request, stage1.id, 'approved', 'LGTM')
    expect(approval.status).toBe('approved')
  })

  test('approve stage 2 → entity becomes approved', async ({ request }) => {
    const stage2 = await findPendingApprovalStage(request, programId, testCaseId, 2)
    await decideApproval(request, stage2.id, 'approved')

    // Entity should now be approved
    const status = await getTestCaseApprovalStatus(request, testCaseId)
    expect(status.status).toBe('approved')
  })

  test('delete workflow', async ({ request }) => {
    const result = await deleteApprovalWorkflow(request, workflowId)
    expect(result.deleted).toBe(true)
  })
})
