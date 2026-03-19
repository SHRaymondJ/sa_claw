import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:8023',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'cd .. && MODEL_PROVIDER=mock ./.venv/bin/python -m uvicorn app.main:app --port 8023',
    url: 'http://127.0.0.1:8023/health',
    reuseExistingServer: false,
  },
  projects: [
    {
      name: 'mobile',
      use: {
        ...devices['iPhone 13'],
      },
    },
    {
      name: 'desktop',
      use: {
        viewport: { width: 1440, height: 1024 },
      },
    },
  ],
})
