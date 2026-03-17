import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.E2E_PORT || '5001'),
  envPrefix: 'E2E',
  dbSlug: 'e2e',
  retries: 1,
})
