import { APIRequestContext, expect } from '@playwright/test'
import { createProgramApprovalSeed, createTestCase } from './testing-seed'

type SeedRecord = Record<string, any>

type CreateApprovalWorkflowOptions = {
  name?: string
  entityType?: string
  stages?: Array<Record<string, any>>
}

export async function createApprovalProgramContext(
  request: APIRequestContext,
  namePrefix = 'E2E Approval Program',
): Promise<{ program: SeedRecord; project: SeedRecord }> {
  return createProgramApprovalSeed(request, namePrefix)
}

export async function createApprovalWorkflow(
  request: APIRequestContext,
  programId: number,
  options: CreateApprovalWorkflowOptions = {},
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/programs/${programId}/approval-workflows`, {
    data: {
      name: options.name || 'TC 2-Stage Review',
      entity_type: options.entityType || 'test_case',
      stages: options.stages || [
        { stage: 1, role: 'Reviewer', required: true },
        { stage: 2, role: 'QA Lead', required: true },
      ],
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function listApprovalWorkflows(
  request: APIRequestContext,
  programId: number,
): Promise<SeedRecord[]> {
  const response = await request.get(`/api/v1/programs/${programId}/approval-workflows`)
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function updateApprovalWorkflow(
  request: APIRequestContext,
  workflowId: number,
  data: Record<string, any>,
): Promise<SeedRecord> {
  const response = await request.put(`/api/v1/approval-workflows/${workflowId}`, {
    data,
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function deleteApprovalWorkflow(
  request: APIRequestContext,
  workflowId: number,
): Promise<SeedRecord> {
  const response = await request.delete(`/api/v1/approval-workflows/${workflowId}`)
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createApprovalTestCase(
  request: APIRequestContext,
  programId: number,
  title = 'E2E Approval TC',
): Promise<SeedRecord> {
  return createTestCase(request, {
    programId,
    title,
    testType: 'Manual',
    testLayer: 'regression',
  })
}

export async function submitEntityForApproval(
  request: APIRequestContext,
  entityType: string,
  entityId: number,
): Promise<SeedRecord> {
  const response = await request.post('/api/v1/approvals/submit', {
    data: { entity_type: entityType, entity_id: entityId },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function listPendingApprovals(
  request: APIRequestContext,
  programId: number,
): Promise<SeedRecord[]> {
  const response = await request.get(`/api/v1/approvals/pending?program_id=${programId}`)
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function getTestCaseApprovalStatus(
  request: APIRequestContext,
  testCaseId: number,
): Promise<SeedRecord> {
  const response = await request.get(`/api/v1/test_case/${testCaseId}/approval-status`)
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function findPendingApprovalStage(
  request: APIRequestContext,
  programId: number,
  entityId: number,
  stage: number,
): Promise<SeedRecord> {
  const pending = await listPendingApprovals(request, programId)
  const record = pending.find((item: any) => item.stage === stage && item.entity_id === entityId)
  expect(record).toBeDefined()
  return record
}

export async function decideApproval(
  request: APIRequestContext,
  approvalId: number,
  decision: string,
  comment?: string,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/approvals/${approvalId}/decide`, {
    data: {
      decision,
      ...(comment ? { comment } : {}),
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}
