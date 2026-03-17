import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.CUTOVER_E2E_PORT || '5016'),
  envPrefix: 'CUTOVER_E2E',
  dbSlug: 'cutover_e2e',
})
