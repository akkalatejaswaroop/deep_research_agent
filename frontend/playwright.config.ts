import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    launchOptions: {
      executablePath: 'C:/Users/Tejas/AppData/Local/ms-playwright/chromium-1223/chrome-win64/chrome.exe',
    },
  },
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: 'python -m uvicorn main:app --host 127.0.0.1 --port 8000',
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true,
      timeout: 90_000,
    },
  ],
});
