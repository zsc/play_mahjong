import { defineConfig } from '@playwright/test';

// This suite consumes dist only. No Python checkpoint, native fixtures or dev server.
export default defineConfig({
  testDir: './tests', testMatch: 'release.spec.ts', timeout: 120000, workers: 1,
  use: { headless: true, launchOptions: { channel: process.env.CI ? undefined : 'chrome' } },
  webServer: {
    command: 'npm run preview -- --port 4174 --base /play_mahjong/',
    url: process.env.STATIC_TEST_URL || 'http://127.0.0.1:4174/play_mahjong/',
    reuseExistingServer: !process.env.CI,
  },
});
