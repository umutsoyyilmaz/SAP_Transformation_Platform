import { APIRequestContext, expect } from '@playwright/test'
import { createProgramContext } from './seed-factory'

type SeedRecord = Record<string, any>

type ProjectPayload = {
  code: string
  name: string
  methodology?: string
  project_type?: string
  sap_product?: string
  deployment_option?: string
  priority?: string
  wave_number?: number
}

type WorkstreamPayload = {
  name: string
  ws_type?: string
  status?: string
  lead_name?: string
  project_id: number
}

type TeamMemberPayload = {
  name: string
  email: string
  role?: string
  project_id: number
}

type WavePayload = {
  name: string
  order: number
  project_id: number
}

export type ProjectSetupSeedContext = {
  program: SeedRecord
  project: SeedRecord
  projects: SeedRecord[]
}

export type DownstreamScopeSeedContext = {
  program: SeedRecord
  project: SeedRecord
  alternateProject: SeedRecord
  activeWave: SeedRecord
  foreignWave: SeedRecord
  activeWaveName: string
  foreignWaveName: string
  activeMember: SeedRecord
  foreignMember: SeedRecord
  activeMemberName: string
  foreignMemberName: string
}

export async function createProgramProject(
  request: APIRequestContext,
  programId: number,
  payload: ProjectPayload,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/programs/${programId}/projects`, {
    data: {
      methodology: 'hybrid',
      project_type: 'bluefield',
      sap_product: 'BTP',
      deployment_option: 'cloud',
      priority: 'high',
      wave_number: 1,
      ...payload,
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createProgramWorkstream(
  request: APIRequestContext,
  programId: number,
  payload: WorkstreamPayload,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/programs/${programId}/workstreams`, {
    data: {
      ws_type: 'functional',
      status: 'active',
      lead_name: 'Jane Lead',
      ...payload,
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createProgramTeamMember(
  request: APIRequestContext,
  programId: number,
  payload: TeamMemberPayload,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/programs/${programId}/team`, {
    data: {
      role: 'stream_lead',
      ...payload,
    },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createProgramWave(
  request: APIRequestContext,
  programId: number,
  payload: WavePayload,
): Promise<SeedRecord> {
  const response = await request.post(`/api/v1/programs/${programId}/waves`, {
    data: payload,
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function createProjectSetupSeedContext(
  request: APIRequestContext,
): Promise<ProjectSetupSeedContext> {
  const stamp = Date.now()
  const { program } = await createProgramContext(request, {
    namePrefix: 'E2E Project Setup',
    methodology: 'sap_activate',
  })

  const projects = await Promise.all([
    createProgramProject(request, program.id, {
      code: `WAVE-${stamp}-0`,
      name: 'Wave 1',
      methodology: 'hybrid',
      wave_number: 1,
    }),
    createProgramProject(request, program.id, {
      code: `WAVE-${stamp}-1`,
      name: 'Wave 2',
      methodology: 'agile',
      wave_number: 2,
    }),
  ])

  return { program, project: projects[0], projects }
}

export async function createProgramLaunchpadSeedContext(
  request: APIRequestContext,
): Promise<ProjectSetupSeedContext> {
  const stamp = Date.now()
  const { program } = await createProgramContext(request, {
    namePrefix: 'E2E Program Launchpad',
    methodology: 'sap_activate',
  })

  const project = await createProgramProject(request, program.id, {
    code: `ROLL-${stamp}`,
    name: 'Wave TR',
    methodology: 'hybrid',
    wave_number: 1,
  })

  return { program, project, projects: [project] }
}

export async function createDownstreamScopeSeedContext(
  request: APIRequestContext,
): Promise<DownstreamScopeSeedContext> {
  const stamp = Date.now()
  const { program, project } = await createProgramContext(request, {
    namePrefix: 'E2E Downstream Scope',
    methodology: 'sap_activate',
  })
  expect(project?.id).toBeTruthy()

  const alternateProject = await createProgramProject(request, program.id, {
    code: `ALT-${stamp}`,
    name: 'Alternate Wave',
    methodology: 'agile',
    sap_product: 'S4',
    priority: 'medium',
    wave_number: 2,
  })

  const activeWaveName = `Active Project Wave ${stamp}`
  const foreignWaveName = `Foreign Project Wave ${stamp}`
  const activeWave = await createProgramWave(request, program.id, {
    name: activeWaveName,
    order: 1,
    project_id: project.id,
  })
  const foreignWave = await createProgramWave(request, program.id, {
    name: foreignWaveName,
    order: 2,
    project_id: alternateProject.id,
  })

  const activeMemberName = `Active Owner ${stamp}`
  const foreignMemberName = `Foreign Owner ${stamp}`
  const activeMember = await createProgramTeamMember(request, program.id, {
    name: activeMemberName,
    email: `active-${stamp}@example.com`,
    role: 'stream_lead',
    project_id: project.id,
  })
  const foreignMember = await createProgramTeamMember(request, program.id, {
    name: foreignMemberName,
    email: `foreign-${stamp}@example.com`,
    role: 'stream_lead',
    project_id: alternateProject.id,
  })

  return {
    program,
    project,
    alternateProject,
    activeWave,
    foreignWave,
    activeWaveName,
    foreignWaveName,
    activeMember,
    foreignMember,
    activeMemberName,
    foreignMemberName,
  }
}
