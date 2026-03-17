import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.DASHBOARD_E2E_PORT || '5014'),
  envPrefix: 'DASHBOARD_E2E',
  dbSlug: 'dashboard_e2e',
})
