import { test, expect } from "@playwright/test";

// NOT YET RUN IN THIS SANDBOX - see the header comment in
// playwright.config.ts. Written against the real login page
// (src/app/(auth)/login/page.tsx) and its actual field labels/copy.

test.describe("Login", () => {
  test("shows validation errors for an empty submission", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Log in" }).click();

    await expect(page.getByText("Email is required")).toBeVisible();
    await expect(page.getByText("Password is required")).toBeVisible();
  });

  test("shows a validation error for a malformed email", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("not-an-email");
    await page.getByLabel("Password").fill("something");
    await page.getByRole("button", { name: "Log in" }).click();

    await expect(page.getByText("Enter a valid email address")).toBeVisible();
  });

  test("toggles password visibility", async ({ page }) => {
    await page.goto("/login");
    const passwordInput = page.getByLabel("Password");
    await expect(passwordInput).toHaveAttribute("type", "password");

    // The eye icon button has no accessible name in the current markup -
    // targeted by position next to the password field instead.
    await page.locator("form").getByRole("button").last().click();
    await expect(passwordInput).toHaveAttribute("type", "text");
  });

  test("redirects to /dashboard on successful login", async ({ page }) => {
    // Requires a real backend running and seeded with a known test user -
    // set E2E_TEST_EMAIL/E2E_TEST_PASSWORD or edit these directly.
    const email = process.env.E2E_TEST_EMAIL ?? "chairman@example.com";
    const password = process.env.E2E_TEST_PASSWORD ?? "changeme123";

    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Log in" }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    await expect(page.getByRole("heading", { name: /^Welcome,/ })).toBeVisible();
  });
});
