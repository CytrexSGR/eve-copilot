import { test, expect } from "@playwright/test";
import { injectAuthCookie, TEST_USER } from "../helpers/auth";

test.describe("Login Flow", () => {

  test("unauthenticated page shows login prompt", async ({ page }) => {
    // Visit the root without auth — RequireAuth should show login screen
    await page.goto("/");
    // The RequireAuth component renders "Login with EVE Online" button
    // and the title "Infinimind Intelligence"
    await expect(
      page.getByText("Infinimind Intelligence")
    ).toBeVisible({ timeout: 15_000 });

    await expect(
      page.getByRole("button", { name: /Login with EVE/i })
    ).toBeVisible();

    // The page should also mention EVE SSO
    await expect(
      page.getByText(/EVE SSO/i)
    ).toBeVisible();
  });

  test("authenticated page shows character portrait and logout", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/");

    // After auth injection the page should load the Layout header.
    // The header contains the account portrait link and a "Logout" button.
    // It also shows the character switcher with both characters (since >1 chars).
    await expect(
      page.getByRole("button", { name: /Logout/i })
    ).toBeVisible({ timeout: 30_000 });

    // The portrait image of the primary character should be rendered in the header
    const portrait = page.locator(
      `img[src*="characters/${TEST_USER.characterId}/portrait"]`
    );
    await expect(portrait.first()).toBeVisible({ timeout: 10_000 });
  });

  test("dashboard/home content is accessible when authenticated", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/");

    // The Home page renders HeroSection and Layout with header.
    // Wait for the header h1 to appear ("Infinimind Intelligence" in the logo).
    await expect(
      page.locator("h1").filter({ hasText: /Infinimind Intelligence/i })
    ).toBeVisible({ timeout: 30_000 });

    // Verify the "Login with EVE Online" button is NOT visible (we are logged in)
    await expect(
      page.getByRole("button", { name: /Login with EVE Online/i })
    ).not.toBeVisible();

    // Footer should be visible as part of the Layout
    await expect(
      page.getByText("Infinimind Creations")
    ).toBeVisible({ timeout: 10_000 });
  });
});
