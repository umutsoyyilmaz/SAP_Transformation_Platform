import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  retries: 1,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: 'http://localhost:5001',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
  webServer: {
    command: 'cd .. && APP_ENV=development DATABASE_URL=sqlite:////Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/instance/sap_platform_dev.db API_AUTH_ENABLED=false .venv/bin/flask run --port 5001',
    url: 'http://localhost:5001/api/v1/health',
    reuseExistingServer: false,
    timeout: 30_000,
  },
})
