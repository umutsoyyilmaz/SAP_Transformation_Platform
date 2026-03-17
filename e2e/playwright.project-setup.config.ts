import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.PROJECT_SETUP_E2E_PORT || '5015'),
  envPrefix: 'PROJECT_SETUP_E2E',
  dbSlug: 'project_setup_e2e',
})
