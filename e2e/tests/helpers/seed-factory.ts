import { APIRequestContext, expect } from '@playwright/test'

type SeedRecord = Record<string, any>

export type ProgramSeedContext = {
  program: SeedRecord
  project: SeedRecord
}

export type ProgramHierarchySeedContext = ProgramSeedContext & {
  l1: SeedRecord
  l2: SeedRecord
  l3: SeedRecord
}

type CreateProgramContextOptions = {
  namePrefix: string
  methodology?: string
  status?: string
  programData?: Record<string, any>
}

type CreateProcessHierarchyOptions = {
  projectId: number
  mutationContext?: string
  l1CodePrefix?: string
  l1Name?: string
  l2CodePrefix?: string
  l2Name?: string
  l3CodePrefix?: string
  l3Name: string
  fitStatus?: string
}

type CreateProgramWithHierarchyOptions = CreateProgramContextOptions & {
  hierarchy: CreateProcessHierarchyOptions
}

export async function createProgramContext(
  request: APIRequestContext,
  options: CreateProgramContextOptions,
): Promise<ProgramSeedContext> {
  const stamp = Date.now()
  const response = await request.post('/api/v1/programs', {
    data: {
      name: `${options.namePrefix} ${stamp}`,
      methodology: options.methodology || 'sap_activate',
      status: options.status || 'active',
      ...(options.programData || {}),
    },
  })
  expect(response.ok()).toBeTruthy()
  const program = await response.json()
  const project = Array.isArray(program.projects) ? program.projects[0] : null
  expect(project?.id).toBeTruthy()
  return { program, project }
}

export async function createProcessHierarchy(
  request: APIRequestContext,
  options: CreateProcessHierarchyOptions,
) {
  const stamp = Date.now()
  const mutationContext = options.mutationContext || 'project_setup'

  const l1Res = await request.post('/api/v1/explore/process-levels', {
    data: {
      project_id: options.projectId,
      mutation_context: mutationContext,
      level: 1,
      code: `${options.l1CodePrefix || 'VC'}-${stamp}`,
      name: options.l1Name || 'Value Chain',
    },
  })
  expect(l1Res.ok()).toBeTruthy()
  const l1 = await l1Res.json()

  const l2Res = await request.post('/api/v1/explore/process-levels', {
    data: {
      project_id: options.projectId,
      mutation_context: mutationContext,
      level: 2,
      parent_id: l1.id,
      code: `${options.l2CodePrefix || 'PA'}-${stamp}`,
      name: options.l2Name || 'Process Area',
    },
  })
  expect(l2Res.ok()).toBeTruthy()
  const l2 = await l2Res.json()

  const l3Payload: Record<string, any> = {
    project_id: options.projectId,
    mutation_context: mutationContext,
    level: 3,
    parent_id: l2.id,
    code: `${options.l3CodePrefix || 'OTC'}-${stamp}`,
    name: options.l3Name,
  }
  if (options.fitStatus) {
    l3Payload.fit_status = options.fitStatus
  }

  const l3Res = await request.post('/api/v1/explore/process-levels', {
    data: l3Payload,
  })
  expect(l3Res.ok()).toBeTruthy()
  const l3 = await l3Res.json()

  return { l1, l2, l3 }
}

export async function createProgramWithHierarchyContext(
  request: APIRequestContext,
  options: CreateProgramWithHierarchyOptions,
): Promise<ProgramHierarchySeedContext> {
  const context = await createProgramContext(request, options)
  const levels = await createProcessHierarchy(request, {
    ...options.hierarchy,
    projectId: context.project.id,
  })
  return { ...context, ...levels }
}
