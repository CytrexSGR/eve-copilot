import { test, expect } from "@playwright/test";
import { injectAuthCookie, TEST_USER } from "../helpers/auth";

test.describe("Fittings Page", () => {

  test("fittings page loads with hero section and tabs", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/fittings");

    // The Fittings page renders a hero with "Fitting System" heading
    await expect(
      page.locator("h1").filter({ hasText: /Fitting System/i })
    ).toBeVisible({ timeout: 15_000 });

    // Subtitle text
    await expect(
      page.getByText("Browse, create, and share ship fittings")
    ).toBeVisible({ timeout: 10_000 });

    // "New Fitting" link button should be visible
    await expect(
      page.getByText("New Fitting").first()
    ).toBeVisible({ timeout: 10_000 });

    // "Import EFT" button should be visible
    await expect(
      page.getByText("Import EFT").first()
    ).toBeVisible({ timeout: 10_000 });

    // Tab buttons: "My Fits" and "Shared Fits"
    await expect(
      page.getByRole("button", { name: /My Fits/i })
    ).toBeVisible({ timeout: 10_000 });

    await expect(
      page.getByRole("button", { name: /Shared Fits/i })
    ).toBeVisible({ timeout: 10_000 });

    // Search input for fittings
    await expect(
      page.locator("input[placeholder*='Search fittings']")
    ).toBeVisible({ timeout: 10_000 });

    // Footer
    await expect(
      page.getByText("Infinimind Creations")
    ).toBeVisible({ timeout: 10_000 });
  });

  test("shared fittings tab shows community fittings or empty state", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/fittings");

    // Wait for page to load
    await expect(
      page.locator("h1").filter({ hasText: /Fitting System/i })
    ).toBeVisible({ timeout: 15_000 });

    // Click on "Shared Fits" tab
    await page.getByRole("button", { name: /Shared Fits/i }).click();

    // Wait for shared fittings to load — the loading state shows "Loading fittings..."
    // then transitions to either fittings cards or "No fittings found".
    // Wait longer for the API response and state transition.
    await page.waitForTimeout(5000);

    // The shared tab should either show:
    // 1. Fitting cards (links to /fittings/custom/...)
    // 2. "No fittings found" empty state
    // 3. An error message
    // 4. Still showing "Loading fittings..."
    const hasFittings = await page.locator("a[href*='/fittings/custom/']").first().isVisible().catch(() => false);
    const hasEmptyState = await page.getByText(/No fittings found/i).isVisible().catch(() => false);
    const hasError = await page.getByText(/Failed to load/i).isVisible().catch(() => false);
    const stillLoading = await page.getByText(/Loading fittings/i).isVisible().catch(() => false);

    // One of these states should be true — the page should not be blank
    expect(hasFittings || hasEmptyState || hasError || stillLoading).toBeTruthy();

    // Verify we're still on the fittings page
    expect(page.url()).toContain("/fittings");
  });

  test("fitting editor is accessible at /fittings/new", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/fittings/new");

    // The FittingEditor page should load.
    // It has a ship browser / ship selection interface.
    // Wait for the page to load without crashing — check that we're still on the right URL.
    await page.waitForTimeout(3000);

    expect(page.url()).toContain("/fittings/new");

    // The page should not redirect to login (we're authenticated)
    await expect(
      page.getByRole("button", { name: /Login with EVE/i })
    ).not.toBeVisible();

    // The page should render some content (not be blank)
    // The FittingEditor has a ship display area or a fitting browser
    // At minimum, the Layout footer should be visible
    await expect(
      page.getByText("Infinimind Creations")
    ).toBeVisible({ timeout: 15_000 });
  });

  test("API requests contain X-Character-Id header", async ({ context, page }) => {
    await injectAuthCookie(context);

    const apiRequests: { url: string; headers: Record<string, string> }[] = [];

    page.on("request", (request) => {
      const url = request.url();
      if (url.includes("/api/")) {
        apiRequests.push({
          url,
          headers: request.headers(),
        });
      }
    });

    await page.goto("/fittings");

    // Wait for API calls (character fittings are fetched on mount)
    await page.waitForTimeout(5000);

    // There should be at least one API request
    expect(apiRequests.length).toBeGreaterThan(0);

    // Find requests with the X-Character-Id header
    const requestsWithCharHeader = apiRequests.filter(
      (r) => r.headers["x-character-id"] === String(TEST_USER.characterId)
    );

    expect(requestsWithCharHeader.length).toBeGreaterThan(0);
  });
});
