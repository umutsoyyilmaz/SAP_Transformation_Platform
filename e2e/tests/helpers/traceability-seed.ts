import { APIRequestContext, expect, Page } from '@playwright/test'
import { expectAppReady, openWithActiveContext, syncActiveContext } from './active-context'
import { createProgramWithHierarchyContext } from './seed-factory'
import { createDefect, createTestCase } from './testing-seed'

type SeedRecord = Record<string, any>

export type BasicTraceabilitySeedContext = {
  program: SeedRecord
  project: SeedRecord
  l3: SeedRecord
  testCase: SeedRecord
}

export type CrossModuleTraceabilitySeedContext = BasicTraceabilitySeedContext & {
  requirement: SeedRecord
  backlogItem: SeedRecord
  defect: SeedRecord
}

type TraceabilityOpenOptions = {
  route?: string
  waitForReady?: boolean
  syncContext?: boolean
  user?: {
    full_name: string
    email: string
    roles: string[]
  }
}

const DEFAULT_TRACEABILITY_USER = {
  full_name: 'Trace E2E User',
  email: 'trace-e2e@example.com',
  roles: ['program_manager', 'test_manager'],
}

async function createRequirement(
  request: APIRequestContext,
  projectId: number,
  l3Id: number,
  label: string,
): Promise<SeedRecord> {
  const response = await request.post('/api/v1/explore/requirements', {
    data: {
      project_id: projectId,
      title: `${label} Explore Requirement`,
      description: 'Traceability requirement for cross-module flow',
      scope_item_id: l3Id,
      priority: 'P1',
      type: 'functional',
      created_by_id: 'e2e',
      created_by_name: 'E2E User',
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

async function transitionRequirement(
  request: APIRequestContext,
  requirementId: number,
  action: string,
  extraData: Record<string, any> = {},
): Promise<void> {
  const response = await request.post(`/api/v1/explore/requirements/${requirementId}/transition`, {
    data: {
      action,
      user_id: 'e2e-user',
      ...extraData,
    },
  })
  expect(response.ok()).toBeTruthy()
}

async function convertRequirementToBacklog(
  request: APIRequestContext,
  requirementId: number,
  projectId: number,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/explore/requirements/${requirementId}/convert`, {
    data: {
      project_id: projectId,
      user_id: 'e2e-user',
      target_type: 'backlog',
      wricef_type: 'enhancement',
      module: 'FI',
    },
  })
  expect(response.ok()).toBeTruthy()
  const body = await response.json()
  expect(body.backlog_item_id).toBeTruthy()

  const backlogResponse = await request.get(`/api/v1/backlog/${body.backlog_item_id}`)
  expect(backlogResponse.ok()).toBeTruthy()
  return backlogResponse.json()
}

export async function createTraceabilitySeed(
  request: APIRequestContext,
  namePrefix: string,
): Promise<BasicTraceabilitySeedContext> {
  const { program, project, l3 } = await createProgramWithHierarchyContext(request, {
    namePrefix,
    methodology: 'agile',
    hierarchy: {
      projectId: 0,
      l3CodePrefix: 'OTC',
      l3Name: 'Order to Cash',
      fitStatus: 'gap',
    },
  })

  const testCase = await createTestCase(request, {
    programId: program.id,
    title: `Traceability Case ${Date.now()}`,
    testLayer: 'sit',
    testType: 'Manual',
    module: 'FI',
    processLevelId: l3.id,
    expectedResult: 'Derived chain renders successfully',
  })

  return { program, project, l3, testCase }
}

export async function createCrossModuleTraceabilitySeed(
  request: APIRequestContext,
  label: string,
): Promise<CrossModuleTraceabilitySeedContext> {
  const { program, project, l3 } = await createProgramWithHierarchyContext(request, {
    namePrefix: `E2E Trace ${label}`,
    methodology: 'agile',
    hierarchy: {
      projectId: 0,
      l3CodePrefix: 'OTC',
      l3Name: 'Order to Cash',
      fitStatus: 'gap',
    },
  })

  const requirement = await createRequirement(request, project.id, l3.id, label)
  await transitionRequirement(request, requirement.id, 'submit_for_review')
  await transitionRequirement(request, requirement.id, 'approve', { approved_by_name: 'E2E Approver' })
  const backlogItem = await convertRequirementToBacklog(request, requirement.id, project.id)

  const testCase = await createTestCase(request, {
    programId: program.id,
    title: `${label} Linked Test Case`,
    testLayer: 'sit',
    module: 'FI',
    processLevelId: l3.id,
    expectedResult: 'Linked downstream artifact works end-to-end',
    extraData: {
      explore_requirement_id: requirement.id,
      backlog_item_id: backlogItem.id,
      traceability_links: [
        {
          l3_process_level_id: String(l3.id),
          explore_requirement_ids: [requirement.id],
          backlog_item_ids: [backlogItem.id],
        },
      ],
    },
  })

  const defect = await createDefect(request, {
    programId: program.id,
    title: `${label} Linked Defect`,
    severity: 'S2',
    module: 'FI',
    testCaseId: testCase.id,
    backlogItemId: backlogItem.id,
    exploreRequirementId: requirement.id,
  })

  return { program, project, l3, requirement, backlogItem, testCase, defect }
}

export async function openTraceabilityContext(
  page: Page,
  context: Pick<BasicTraceabilitySeedContext, "program" | "project">,
  options: TraceabilityOpenOptions = {},
): Promise<void> {
  const {
    route,
    waitForReady = true,
    syncContext = false,
    user = DEFAULT_TRACEABILITY_USER,
  } = options

  await openWithActiveContext(page, context, { route, user })
  if (syncContext) {
    await syncActiveContext(page, context)
  }
  if (waitForReady) {
    await expectAppReady(page)
  }
}
