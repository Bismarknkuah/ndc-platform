import { test, expect } from "@playwright/test";

// NOT YET RUN IN THIS SANDBOX - see the header comment in
// playwright.config.ts.
//
// These assume an authenticated session. Playwright's standard pattern
// is a setup project that logs in once and saves storage state; wire
// that up via `playwright.config.ts`'s `projects` + a
// `test.beforeAll`/global-setup script before running these for real.

test.describe("Unauthenticated access", () => {
  test("redirects straight to /login when visiting the root with no session", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("redirects to /login when visiting a protected route directly", async ({ page }) => {
    await page.goto("/members");
    await expect(page).toHaveURL(/\/login/);
  });

  test("shows a real 404 page for an unknown route", async ({ page }) => {
    const response = await page.goto("/this-route-does-not-exist");
    expect(response?.status()).toBe(404);
    await expect(page.getByText("404")).toBeVisible();
  });
});

test.describe("Command palette", () => {
  test.skip(
    true,
    "Requires an authenticated session - see the module-level note on wiring up storageState.",
  );

  test("opens with Cmd/Ctrl+K and navigates to a page", async ({ page }) => {
    await page.goto("/dashboard");
    await page.keyboard.press("ControlOrMeta+k");
    await expect(page.getByPlaceholder(/search pages, members/i)).toBeVisible();

    await page.getByText("Hierarchy").click();
    await expect(page).toHaveURL(/\/hierarchy/);
  });
});
