import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  forbidOnly: true,
  timeout: 30000,
  globalTimeout: 300000,
  retries: 0,
  workers: 2,
  reporter: [
    ['list'],
    ['json', { outputFile: '/results/results.json' }],
    ['html', { outputFolder: '/results/html', open: 'never' }],
  ],
  outputDir: '/results/test-results',
  use: {
    baseURL: 'http://127.0.0.1:3000',
    browserName: 'chromium',
    headless: true,
    launchOptions: { args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'mobile360',
      use: {
        viewport: { width: 360, height: 820 },
        browserName: 'chromium',
        isMobile: false,
        hasTouch: false,
        userAgent: undefined,
        deviceScaleFactor: undefined,
      },
    },
    {
      name: 'mobile375',
      use: {
        viewport: { width: 375, height: 820 },
        browserName: 'chromium',
        isMobile: false,
        hasTouch: false,
        userAgent: undefined,
        deviceScaleFactor: undefined,
      },
    },
    {
      name: 'desktop',
      use: {
        viewport: { width: 1365, height: 900 },
        browserName: 'chromium',
        isMobile: false,
        hasTouch: false,
      },
    },
  ],
  webServer: {
    command: 'pnpm --dir /app/apps/web exec next start -H 127.0.0.1 -p 3000',
    url: 'http://127.0.0.1:3000',
    timeout: 60000,
    reuseExistingServer: false,
  },
});
