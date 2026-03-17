import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.FE_SPRINT3_E2E_PORT || '5021'),
  envPrefix: 'FE_SPRINT3_E2E',
  dbSlug: 'fe_sprint3_e2e',
})
