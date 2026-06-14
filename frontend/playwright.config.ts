import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(frontendDir, '..')
const backendDir = path.join(repoRoot, 'backend')

const backendCommand = [
  `cd "${backendDir}"`,
  'source venv/bin/activate',
  'set -a',
  '[ -f .env ] && source .env',
  'set +a',
  'AUTH_BYPASS_ENABLED=true SCRAPER_MODE=fixtures uvicorn main:app --host 0.0.0.0 --port 8000',
].join(' && ')

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `bash -lc '${backendCommand}'`,
      url: 'http://localhost:8000/health',
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      cwd: repoRoot,
    },
    {
      command: 'npm run dev -- --port 3000 --strictPort',
      url: 'http://localhost:3000',
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      cwd: frontendDir,
    },
  ],
})
