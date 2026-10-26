import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './tests', testIgnore: 'release.spec.ts', timeout: 120000, workers: 1,
  use: { baseURL: 'http://127.0.0.1:5173', headless: true, launchOptions: { channel: 'chrome' } } });
