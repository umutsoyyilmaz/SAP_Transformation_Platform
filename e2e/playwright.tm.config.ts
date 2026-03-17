import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.TM_E2E_PORT || '5011'),
  envPrefix: 'TM_E2E',
  dbSlug: 'tm_e2e',
})
