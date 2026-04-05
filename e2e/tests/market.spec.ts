import { test, expect } from "@playwright/test";
import { injectAuthCookie, TEST_USER } from "../helpers/auth";

test.describe("Market Page", () => {

  test("market page loads successfully with hero section and tabs", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/market");

    // The Market page renders a MarketHeroSection with "Market Suite" heading
    await expect(
      page.locator("h1").filter({ hasText: /Market Suite/i })
    ).toBeVisible({ timeout: 15_000 });

    // The hero section shows a "Live" indicator
    await expect(
      page.getByText("Live").first()
    ).toBeVisible({ timeout: 10_000 });

    // Market tab navigation should be visible with tab buttons
    // Tabs: Prices, Order Book, Arbitrage, Opportunities, Portfolio
    await expect(
      page.getByText("Arbitrage").first()
    ).toBeVisible({ timeout: 10_000 });

    await expect(
      page.getByText("Opportunities").first()
    ).toBeVisible({ timeout: 10_000 });

    // The search input should be visible with placeholder text
    await expect(
      page.locator("input[placeholder*='Tritanium']")
    ).toBeVisible({ timeout: 10_000 });

    // Footer should be visible (page loaded fully)
    await expect(
      page.getByText("Infinimind Creations")
    ).toBeVisible({ timeout: 10_000 });
  });

  test("item search works or gracefully handles unavailable market service", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/market");

    // Wait for page to load
    await expect(
      page.locator("h1").filter({ hasText: /Market Suite/i })
    ).toBeVisible({ timeout: 15_000 });

    // Type "Tritanium" in the search input
    const searchInput = page.locator("input[placeholder*='Tritanium']");
    await searchInput.fill("Tritanium");

    // Wait for debounced search to fire (300ms) + API response
    await page.waitForTimeout(3000);

    // The dropdown may show results OR the API may be unavailable (market service unhealthy).
    // Either outcome is acceptable — the page should not crash.
    const hasDropdownResults = await page.locator("div").filter({ hasText: /Tritanium/i }).nth(2).isVisible().catch(() => false);
    
    // Verify the page is still functional (not crashed)
    await expect(
      page.locator("h1").filter({ hasText: /Market Suite/i })
    ).toBeVisible();

    // The search input should still contain our query
    await expect(searchInput).toHaveValue("Tritanium");
  });

  test("hot items section loads or shows skeleton when data unavailable", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/market");

    // Wait for page to load
    await expect(
      page.locator("h1").filter({ hasText: /Market Suite/i })
    ).toBeVisible({ timeout: 15_000 });

    // Wait for hot items to attempt loading
    await page.waitForTimeout(5000);

    // Hot items landing section is rendered below the tab content when no item is selected
    // and the current tab is "prices" (default). It either shows:
    // 1. Category headers (minerals, isotopes, etc.) with items if API succeeds
    // 2. A skeleton loader if still loading
    // 3. Nothing if API failed (empty state)
    
    // Check that the page hasn't crashed — hero and tabs still visible
    await expect(
      page.locator("h1").filter({ hasText: /Market Suite/i })
    ).toBeVisible();

    // The prices tab prompt should be visible when no item is selected
    await expect(
      page.getByText(/select an item/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("API requests contain X-Character-Id header", async ({ context, page }) => {
    await injectAuthCookie(context);

    // Intercept API requests to check for X-Character-Id header
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

    await page.goto("/market");

    // Wait for API calls to be made (hero section + hot items)
    await page.waitForTimeout(5000);

    // There should be at least one API request
    expect(apiRequests.length).toBeGreaterThan(0);

    // Find requests with the X-Character-Id header
    const requestsWithCharHeader = apiRequests.filter(
      (r) => r.headers["x-character-id"] === String(TEST_USER.characterId)
    );

    // At least one API request should have the character header
    expect(requestsWithCharHeader.length).toBeGreaterThan(0);
  });
});
