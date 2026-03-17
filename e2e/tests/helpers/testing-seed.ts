import { APIRequestContext, expect } from '@playwright/test'
import { createProgramContext, createProgramWithHierarchyContext } from './seed-factory'

type SeedRecord = Record<string, any>

type CreateTestCaseOptions = {
  programId: number
  title: string
  testLayer?: string
  testType?: string
  module?: string
  processLevelId?: number
  expectedResult?: string
  description?: string
  priority?: string
  extraData?: Record<string, any>
}

type CreateTestPlanOptions = {
  programId: number
  name: string
  description?: string
  planType?: string
  environment?: string
}

type CreateTestCycleOptions = {
  planId: number
  name: string
  testLayer?: string
  cycleType?: string
  status?: string
}

type CreateTestSuiteOptions = {
  programId: number
  name: string
  purpose?: string
  module?: string
}

type CreateTestExecutionOptions = {
  cycleId: number
  testCaseId: number
  result?: string
  executedBy?: string
  notes?: string
}

type CreateDefectOptions = {
  programId: number
  title: string
  severity?: string
  status?: string
  module?: string
  testCaseId?: number
  backlogItemId?: number
  exploreRequirementId?: number
  executionId?: number
}

type CreateBacklogItemOptions = {
  programId: number
  projectId: number
  title: string
  wricefType?: string
  module?: string
  technicalNotes?: string
}

type CreateTestingWorkflowSeedOptions = {
  label: string
  methodology?: string
  module?: string
  l3CodePrefix?: string
  l3Name?: string
  fitStatus?: string
  testLayer?: string
}

type CreateTestingSmokeSeedOptions = {
  label?: string
  methodology?: string
  module?: string
  l3CodePrefix?: string
  l3Name?: string
  fitStatus?: string
  testLayer?: string
  planEnvironment?: string
}

export type TestingWorkflowSeedContext = {
  program: SeedRecord
  project: SeedRecord
  l3: SeedRecord
  plan: SeedRecord
  cycle: SeedRecord
  testCase: SeedRecord
  execution: SeedRecord
}

export type TestingSmokeSeedContext = {
  program: SeedRecord
  project: SeedRecord
  l3: SeedRecord
  plan: SeedRecord
  cycle: SeedRecord
  testCase: SeedRecord
  suite: SeedRecord
  defect: SeedRecord
  backlogItem: SeedRecord
}

export async function createTestCase(
  request: APIRequestContext,
  options: CreateTestCaseOptions,
): Promise<SeedRecord> {
  const payload: Record<string, any> = {
    title: options.title,
    test_layer: options.testLayer || 'sit',
    test_type: options.testType || 'Manual',
  }
  if (options.module) payload.module = options.module
  if (options.processLevelId) payload.process_level_id = options.processLevelId
  if (options.expectedResult) payload.expected_result = options.expectedResult
  if (options.description) payload.description = options.description
  if (options.priority) payload.priority = options.priority
  Object.assign(payload, options.extraData || {})

  const response = await request.post(`/api/v1/programs/${options.programId}/testing/catalog`, {
    data: payload,
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createTestCaseStep(
  request: APIRequestContext,
  testCaseId: number,
  data: Record<string, any>,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/testing/catalog/${testCaseId}/steps`, {
    data,
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createTestPlan(
  request: APIRequestContext,
  options: CreateTestPlanOptions,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/programs/${options.programId}/testing/plans`, {
    data: {
      name: options.name,
      description: options.description,
      plan_type: options.planType || 'sit',
      environment: options.environment,
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createTestCycle(
  request: APIRequestContext,
  options: CreateTestCycleOptions,
): Promise<SeedRecord> {
  const payload: Record<string, any> = {
    name: options.name,
  }
  if (options.status) payload.status = options.status
  if (options.cycleType) {
    payload.cycle_type = options.cycleType
  } else {
    payload.test_layer = options.testLayer || 'sit'
  }

  const response = await request.post(`/api/v1/testing/plans/${options.planId}/cycles`, {
    data: payload,
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createTestSuite(
  request: APIRequestContext,
  options: CreateTestSuiteOptions,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/programs/${options.programId}/testing/suites`, {
    data: {
      name: options.name,
      purpose: options.purpose || 'SIT',
      module: options.module || 'FI',
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function addTestCaseToSuite(
  request: APIRequestContext,
  suiteId: number,
  testCaseId: number,
): Promise<void> {
  const response = await request.post(`/api/v1/testing/suites/${suiteId}/cases`, {
    data: { test_case_id: testCaseId },
  })
  expect(response.ok()).toBeTruthy()
}

export async function createTestExecution(
  request: APIRequestContext,
  options: CreateTestExecutionOptions,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/testing/cycles/${options.cycleId}/executions`, {
    data: {
      test_case_id: options.testCaseId,
      result: options.result || 'fail',
      executed_by: options.executedBy || 'E2E Tester',
      notes: options.notes || 'E2E seeded execution',
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createDefect(
  request: APIRequestContext,
  options: CreateDefectOptions,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/programs/${options.programId}/testing/defects`, {
    data: {
      title: options.title,
      severity: options.severity || 'S2',
      status: options.status || 'open',
      module: options.module || 'FI',
      test_case_id: options.testCaseId,
      backlog_item_id: options.backlogItemId,
      explore_requirement_id: options.exploreRequirementId,
      execution_id: options.executionId,
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createDefectComment(
  request: APIRequestContext,
  defectId: number,
  body: string,
  author = 'E2E User',
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/testing/defects/${defectId}/comments`, {
    data: { author, body },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createBacklogItem(
  request: APIRequestContext,
  options: CreateBacklogItemOptions,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/programs/${options.programId}/backlog`, {
    data: {
      project_id: options.projectId,
      title: options.title,
      wricef_type: options.wricefType || 'workflow',
      module: options.module || 'FI',
      technical_notes: options.technicalNotes || 'Step 1\nStep 2',
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createTestingWorkflowSeed(
  request: APIRequestContext,
  options: CreateTestingWorkflowSeedOptions,
): Promise<TestingWorkflowSeedContext> {
  const moduleCode = options.module || 'FI'
  const { program, project, l3 } = await createProgramWithHierarchyContext(request, {
    namePrefix: `E2E TM Workflow ${options.label}`,
    methodology: options.methodology || 'agile',
    hierarchy: {
      projectId: 0,
      l1CodePrefix: 'L1',
      l2CodePrefix: 'L2',
      l3CodePrefix: options.l3CodePrefix || 'OTC',
      l3Name: options.l3Name || 'Order to Cash',
      fitStatus: options.fitStatus || 'gap',
    },
  })

  const testCase = await createTestCase(request, {
    programId: program.id,
    title: `${options.label} Case`,
    testLayer: options.testLayer || 'sit',
    module: moduleCode,
    processLevelId: l3.id,
    expectedResult: 'Document posts successfully',
  })

  await createTestCaseStep(request, testCase.id, {
    action: 'Execute core finance posting scenario',
    expected_result: 'Posting succeeds without defect',
  })

  const plan = await createTestPlan(request, {
    programId: program.id,
    name: `${options.label} Plan`,
    description: 'Workflow E2E plan',
    planType: options.testLayer || 'sit',
  })

  const cycle = await createTestCycle(request, {
    planId: plan.id,
    name: `${options.label} Cycle`,
    testLayer: options.testLayer || 'sit',
    status: 'in_progress',
  })

  const execution = await createTestExecution(request, {
    cycleId: cycle.id,
    testCaseId: testCase.id,
    result: 'fail',
    executedBy: 'E2E Tester',
    notes: 'Workflow seed execution',
  })

  return { program, project, l3, plan, cycle, testCase, execution }
}

export async function createTestingSmokeSeed(
  request: APIRequestContext,
  options: CreateTestingSmokeSeedOptions = {},
): Promise<TestingSmokeSeedContext> {
  const label = options.label || 'FE Sprint3'
  const moduleCode = options.module || 'MM'
  const { program, project, l3 } = await createProgramWithHierarchyContext(request, {
    namePrefix: `E2E ${label}`,
    methodology: options.methodology || 'sap_activate',
    hierarchy: {
      projectId: 0,
      l3CodePrefix: options.l3CodePrefix || moduleCode,
      l3Name: options.l3Name || 'Materials Management',
      fitStatus: options.fitStatus || 'fit',
    },
  })

  const plan = await createTestPlan(request, {
    programId: program.id,
    name: `E2E ${label} Plan`,
    planType: options.testLayer || 'sit',
    environment: options.planEnvironment || 'QAS',
  })

  const cycle = await createTestCycle(request, {
    planId: plan.id,
    name: `E2E ${label} Cycle`,
    cycleType: options.testLayer || 'sit',
  })

  const testCase = await createTestCase(request, {
    programId: program.id,
    title: `${label} Case ${Date.now()}`,
    testLayer: options.testLayer || 'sit',
    module: moduleCode,
    processLevelId: l3.id,
    expectedResult: 'Smoke flow renders correctly',
  })

  const suite = await createTestSuite(request, {
    programId: program.id,
    name: `${label} Suite ${Date.now()}`,
    purpose: (options.testLayer || 'sit').toUpperCase(),
    module: moduleCode,
  })
  await addTestCaseToSuite(request, suite.id, testCase.id)

  const defect = await createDefect(request, {
    programId: program.id,
    title: `${label} Defect ${Date.now()}`,
    severity: 'P2',
    status: 'open',
    testCaseId: testCase.id,
    module: moduleCode,
  })
  await createDefectComment(request, defect.id, 'Seeded defect comment', 'E2E Smoke')

  const backlogItem = await createBacklogItem(request, {
    programId: program.id,
    projectId: project.id,
    title: `${label} WRICEF ${Date.now()}`,
    wricefType: 'workflow',
    module: moduleCode,
    technicalNotes: 'Step 1: Create PR\nStep 2: Approve workflow',
  })

  return { program, project, l3, plan, cycle, testCase, suite, defect, backlogItem }
}

export async function createProgramApprovalSeed(
  request: APIRequestContext,
  namePrefix: string,
): Promise<{ program: SeedRecord; project: SeedRecord }> {
  return createProgramContext(request, {
    namePrefix,
    methodology: 'agile',
  })
}
