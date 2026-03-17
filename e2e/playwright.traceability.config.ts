import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.TRACEABILITY_E2E_PORT || '5019'),
  envPrefix: 'TRACEABILITY_E2E',
  dbSlug: 'traceability_e2e',
})
