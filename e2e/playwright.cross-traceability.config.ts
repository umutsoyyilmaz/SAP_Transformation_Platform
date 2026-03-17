import { buildIsolatedPlaywrightConfig } from './playwright.shared'

export default buildIsolatedPlaywrightConfig({
  port: Number(process.env.CROSS_TRACE_E2E_PORT || '5022'),
  envPrefix: 'CROSS_TRACE_E2E',
  dbSlug: 'cross_trace_e2e',
})
