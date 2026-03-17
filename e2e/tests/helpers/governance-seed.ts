import { APIRequestContext, expect, Page } from '@playwright/test'
import { openWithActiveContext } from './active-context'
import { createProgramContext } from './seed-factory'

type SeedRecord = Record<string, any>

export type GovernanceSeedContext = {
  program: SeedRecord
  project: SeedRecord
}

export type SteerCoReportDraft = {
  title: string
  status: string
  reportDate: string
  rag: string
  executiveSummary: string
}

export type SavedReportDefinitionDraft = {
  name: string
  description: string
}

export async function createGovernanceSeedContext(
  request: APIRequestContext,
  namePrefix = 'E2E Governance',
): Promise<GovernanceSeedContext> {
  return createProgramContext(request, {
    namePrefix,
    methodology: 'sap_activate',
  })
}

export async function openGovernanceContext(
  page: Page,
  context: GovernanceSeedContext,
): Promise<void> {
  await openWithActiveContext(page, context, {
    user: {
      full_name: 'E2E Governance User',
      email: 'governance@example.com',
      roles: ['program_manager'],
    },
  })
}

export async function bootstrapGovernanceContext(
  page: Page,
  request: APIRequestContext,
  namePrefix = 'E2E Governance',
): Promise<GovernanceSeedContext> {
  const context = await createGovernanceSeedContext(request, namePrefix)
  await openGovernanceContext(page, context)
  return context
}

export async function openGovernanceReportsWorkspace(page: Page): Promise<void> {
  await page.locator('#sidebar [data-view="reports"]').click()
  await expect(page.locator('[data-testid="governance-reports-page"]')).toBeVisible({ timeout: 20000 })
}

export async function expectGovernanceReportsShell(page: Page): Promise<void> {
  await openGovernanceReportsWorkspace(page)
  await expect(page.locator('[data-testid="governance-nav"]')).toContainText('RAID')
  await expect(page.locator('[data-testid="governance-reports-tabs"]')).toContainText('SteerCo Reports')
  await expect(page.locator('[data-testid="governance-reports-page"]')).toContainText('Report Library')
}

export async function openProgramSnapshotAndExpectHealthSummary(
  page: Page,
  summaryText = 'Health Summary',
): Promise<void> {
  await page.getByRole('button', { name: 'Program Snapshot' }).click()
  await expect(page.locator('[data-testid="governance-program-snapshot"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="governance-program-snapshot"]')).toContainText(summaryText)
}

export async function openRaidWorkspaceAndExpectShell(page: Page): Promise<void> {
  await page.locator('[data-testid="governance-nav"] [data-governance-view="raid"]').click()
  await expect(page.locator('[data-testid="governance-raid-page"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="governance-raid-tabs"]')).toContainText('Risks')
  await expect(page.locator('[data-testid="governance-raid-tabs"]')).toContainText('Decisions')
  await expect(page.locator('#sidebar [data-view="raid"]')).toHaveClass(/active/)
  await expect(page.locator('[data-testid="raid-ai-risk-trigger"]')).toBeVisible()
}

export async function runGovernanceAIRiskAssessment(page: Page): Promise<void> {
  await page.evaluate(() => RaidView.runAIRiskAssessment())
  await expect(page.locator('#raidAiRiskResult')).toBeVisible()
}

export async function expectGovernanceShellWithRaidAndRiskAssessment(
  page: Page,
  summaryText = 'Health Summary',
): Promise<void> {
  await expectGovernanceReportsShell(page)
  await openProgramSnapshotAndExpectHealthSummary(page, summaryText)
  await openRaidWorkspaceAndExpectShell(page)
  await runGovernanceAIRiskAssessment(page)
}

export async function openSteerCoReportsWorkspace(page: Page): Promise<void> {
  await openGovernanceReportsWorkspace(page)
  await page.getByRole('button', { name: 'SteerCo Reports' }).click()
  await expect(page.getByRole('heading', { name: 'SteerCo Report Lifecycle' })).toBeVisible()
}

export function buildSteerCoReportDraft(
  overrides: Partial<SteerCoReportDraft> = {},
): SteerCoReportDraft {
  return {
    title: `SteerCo E2E ${Date.now()}`,
    status: 'in_review',
    reportDate: '2026-03-08',
    rag: 'Amber',
    executiveSummary: 'Governance smoke summary',
    ...overrides,
  }
}

export function buildSavedReportDefinitionDraft(
  overrides: Partial<SavedReportDefinitionDraft> = {},
): SavedReportDefinitionDraft {
  return {
    name: `Saved Report ${Date.now()}`,
    description: 'Governance smoke saved preset',
    ...overrides,
  }
}

export async function createSteerCoReportFromWorkspace(
  page: Page,
  draft: SteerCoReportDraft,
): Promise<void> {
  await openSteerCoReportsWorkspace(page)
  await page.locator('[data-testid="reports-open-steerco-modal"]').click()
  await expect(page.locator('[data-testid="reports-steerco-modal"]')).toBeVisible()
  await expect(page.locator('#programReportTitle')).toBeVisible()
  await page.locator('#programReportTitle').fill(draft.title)
  await page.locator('#programReportStatus').selectOption(draft.status)
  await page.locator('#programReportDate').fill(draft.reportDate)
  await page.locator('#programReportRag').selectOption(draft.rag)
  await page.locator('#programReportExecutiveSummary').fill(draft.executiveSummary)
  await page.locator('[data-testid="reports-save-steerco-report"]').click()
}

export async function openAISteeringPack(page: Page): Promise<void> {
  await openGovernanceReportsWorkspace(page)
  await page.getByRole('button', { name: 'AI Steering Pack' }).click()
  await expect(page.locator('[data-testid="reports-ai-steering-pack-modal"]')).toBeVisible()
}

export async function generateAISteeringPack(page: Page): Promise<void> {
  await openAISteeringPack(page)
  await page.locator('[data-testid="reports-ai-steering-pack-generate"]').click()
}

export async function generateAISteeringPackAndExpectSummary(
  page: Page,
  summaryText = 'Executive Summary',
): Promise<void> {
  await generateAISteeringPack(page)
  await expect(page.locator('[data-testid="reports-ai-steering-pack-result"]')).toContainText(summaryText, {
    timeout: 20000,
  })
}

export async function openSaveCurrentReportModal(
  page: Page,
  presetTestId?: string,
): Promise<void> {
  await openGovernanceReportsWorkspace(page)
  const presetButton = presetTestId
    ? page.locator(`[data-testid="reports-preset-button-${presetTestId}"]`)
    : page.locator('[data-testid^="reports-preset-button-"]').first()
  await presetButton.click()
  await expect(page.locator('[data-testid="reports-save-current-report-trigger"]')).toBeVisible({ timeout: 20000 })
  await page.locator('[data-testid="reports-save-current-report-trigger"]').click()
  await expect(page.locator('[data-testid="reports-save-definition-modal"]')).toBeVisible()
}

export async function saveCurrentReportDefinition(
  page: Page,
  draft: SavedReportDefinitionDraft,
  presetTestId?: string,
): Promise<void> {
  await openSaveCurrentReportModal(page, presetTestId)
  await page.locator('#reportSaveName').fill(draft.name)
  await page.locator('#reportSaveDescription').fill(draft.description)
  await page.locator('[data-testid="reports-save-definition-confirm"]').click()
}

export async function saveCurrentReportAndExpectSavedDefinition(
  page: Page,
  draft: SavedReportDefinitionDraft,
  presetTestId?: string,
): Promise<void> {
  await saveCurrentReportDefinition(page, draft, presetTestId)
  await expect(page.locator('#reportContent')).toContainText('Reusable Reports', { timeout: 20000 })
  await expect(page.locator('#reportContent')).toContainText(draft.name)
  await expect(page.locator('#reportContent')).toContainText(draft.description)
}

export async function runSavedReportDefinitionAndExpectResult(
  page: Page,
  draft: SavedReportDefinitionDraft,
  resultTitle = 'Coverage by Module',
): Promise<void> {
  const savedCard = page.locator('.governance-report-card').filter({ hasText: draft.name }).first()
  await expect(savedCard).toBeVisible({ timeout: 20000 })
  await savedCard.getByRole('button', { name: 'Run' }).click()
  await expect(page.locator('#presetResult')).toContainText(resultTitle, { timeout: 20000 })
}

export async function saveCurrentReportAndExpectReusableResult(
  page: Page,
  draft: SavedReportDefinitionDraft,
  presetTestId?: string,
  resultTitle = 'Coverage by Module',
): Promise<void> {
  await saveCurrentReportAndExpectSavedDefinition(page, draft, presetTestId)
  await runSavedReportDefinitionAndExpectResult(page, draft, resultTitle)
}

export async function saveCoverageByModuleReportAndExpectReusableResult(
  page: Page,
  draft: SavedReportDefinitionDraft = buildSavedReportDefinitionDraft(),
): Promise<void> {
  await saveCurrentReportAndExpectReusableResult(page, draft, 'coverage_by_module', 'Coverage by Module')
}

export async function expectSteerCoReportCard(
  page: Page,
  draft: Pick<SteerCoReportDraft, "title">,
  statusLabel = 'In Review',
): Promise<void> {
  await expect(page.locator('[data-testid="program-report-grid"]')).toBeVisible({ timeout: 20000 })
  await expect(page.locator('[data-testid="program-report-card"]')).toContainText(draft.title)
  await expect(page.locator('[data-testid="program-report-card"]')).toContainText(statusLabel)
}

export async function createAndExpectSteerCoReport(
  page: Page,
  draft: SteerCoReportDraft,
  statusLabel = 'In Review',
): Promise<void> {
  await createSteerCoReportFromWorkspace(page, draft)
  await expectSteerCoReportCard(page, draft, statusLabel)
}

export async function createDefaultSteerCoReportAndExpectCard(
  page: Page,
  overrides: Partial<SteerCoReportDraft> = {},
  statusLabel = 'In Review',
): Promise<void> {
  const draft = buildSteerCoReportDraft(overrides)
  await createAndExpectSteerCoReport(page, draft, statusLabel)
}
