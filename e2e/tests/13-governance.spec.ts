/**
 * E2E Flow 13: Governance shell — RAID and Reports
 */
import { test } from '@playwright/test'
import {
  bootstrapGovernanceContext,
  createDefaultSteerCoReportAndExpectCard,
  expectGovernanceShellWithRaidAndRiskAssessment,
  generateAISteeringPackAndExpectSummary,
  saveCoverageByModuleReportAndExpectReusableResult,
} from './helpers/governance-seed'

test('governance shell exposes reports and raid workspaces', async ({ page, request }) => {
  await bootstrapGovernanceContext(page, request)

  await expectGovernanceShellWithRaidAndRiskAssessment(page)
})

test('reports workspace opens ai steering pack modal and returns a summary', async ({ page, request }) => {
  await bootstrapGovernanceContext(page, request)

  await generateAISteeringPackAndExpectSummary(page)
})

test('report library preset can be saved to the reusable reports library', async ({ page, request }) => {
  await bootstrapGovernanceContext(page, request)

  await saveCoverageByModuleReportAndExpectReusableResult(page)
})

test('steerco reports can be created from governance reports workspace', async ({ page, request }) => {
  await bootstrapGovernanceContext(page, request)
  await createDefaultSteerCoReportAndExpectCard(page)
})
