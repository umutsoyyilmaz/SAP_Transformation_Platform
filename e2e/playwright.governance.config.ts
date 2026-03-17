import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.GOVERNANCE_E2E_PORT || '5013'),
  envPrefix: 'GOVERNANCE_E2E',
  dbSlug: 'governance_e2e',
})
