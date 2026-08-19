import { defineConfig, devices } from "@playwright/test";

/**
 * IMPORTANT - read before running:
 * These specs were written against the real app but never executed in
 * the sandbox that built this project - there was no reachable
 * headless-browser binary to download (same network restriction that
 * blocks Google Fonts and the shadcn CLI elsewhere in this codebase).
 * `npx playwright install chromium` was attempted and silently produced
 * no browser. Run `npm run test:e2e` yourself locally/in CI once a
 * browser can actually be installed - don't assume these pass.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run build && npm run start",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
