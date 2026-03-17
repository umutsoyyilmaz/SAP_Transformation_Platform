import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.EXPLORE_E2E_PORT || '5012'),
  envPrefix: 'EXPLORE_E2E',
  dbSlug: 'explore_e2e',
})
