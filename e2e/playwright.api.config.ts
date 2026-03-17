import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.API_E2E_PORT || '5018'),
  envPrefix: 'API_E2E',
  dbSlug: 'api_e2e',
})
