import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.BACKLOG_E2E_PORT || '5017'),
  envPrefix: 'BACKLOG_E2E',
  dbSlug: 'backlog_e2e',
})
