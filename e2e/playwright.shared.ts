import os from 'node:os'
import path from 'node:path'

import { defineConfig } from '@playwright/test'

type IsolatedPlaywrightOptions = {
  port: number
  envPrefix: string
  dbSlug: string
  retries?: number
  workers?: number
}

export function buildIsolatedPlaywrightConfig({
  port,
  envPrefix,
  dbSlug,
  retries = 0,
  workers = 1,
}: IsolatedPlaywrightOptions) {
  const repoRoot = path.resolve(process.cwd(), '..')
  const runId = process.env[`${envPrefix}_RUN_ID`] || `${Date.now()}`
  const dbPath = process.env[`${envPrefix}_DB_PATH`] || path.join(os.tmpdir(), `sap_${dbSlug}_${runId}.db`)
  const dbUrl = `sqlite:///${dbPath}`
  const baseURL = `http://127.0.0.1:${port}`
  const artifactSlug = `${dbSlug}_${runId}`
  const reportDir = path.resolve(process.cwd(), 'playwright-report', artifactSlug)
  const outputDir = path.resolve(process.cwd(), 'test-results', artifactSlug)

  return defineConfig({
    testDir: './tests',
    fullyParallel: false,
    retries,
    workers,
    outputDir,
    reporter: [['html', { open: 'never', outputFolder: reportDir }], ['list']],
    use: {
      baseURL,
      trace: 'retain-on-failure',
      screenshot: 'only-on-failure',
    },
    projects: [
      { name: 'chromium', use: { browserName: 'chromium' } },
    ],
    webServer: {
      command: `cd ${repoRoot} && APP_ENV=testing TEST_DATABASE_URL='${dbUrl}' API_AUTH_ENABLED=false .venv/bin/flask run --port ${port} --no-debugger --no-reload`,
      url: `${baseURL}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
  })
}
