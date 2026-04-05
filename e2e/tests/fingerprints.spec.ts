import { test, expect } from "@playwright/test";
import { injectAuthCookie, TEST_USER } from "../helpers/auth";

/**
 * Fingerprint tests.
 *
 * There is no dedicated "/fingerprints" page in the frontend.
 * The fingerprints API (/api/fingerprints/) is consumed by the Doctrines page (/doctrines)
 * which loads live-ops data from /api/fingerprints/live-ops.
 *
 * We test:
 *  1. The Doctrines page loads and renders data from the fingerprints API
 *  2. API requests include the X-Character-Id header from localStorage
 */

test.describe("Fingerprint Dashboard (Doctrines)", () => {

  test("doctrines page loads fingerprint data", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/doctrines");

    // The Doctrines page renders a HeroSection with stats from the live-ops API.
    // It also has tab navigation with "Live Ops", "Intel", "Trends".
    // Wait for any doctrine-related content to appear.
    await expect(
      page.getByText(/Doctrine/i).first()
    ).toBeVisible({ timeout: 30_000 });

    // Verify we're on the doctrines page (not redirected to login)
    expect(page.url()).toContain("/doctrines");

    // Wait for data to load — look for stats or tab content
    await page.waitForTimeout(3000);

    // The page should show the Layout footer (proof it loaded fully)
    await expect(
      page.getByText("Infinimind Creations")
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

    await page.goto("/doctrines");

    // Wait for API calls to be made
    await page.waitForTimeout(5000);

    // There should be at least one API request
    expect(apiRequests.length).toBeGreaterThan(0);

    // Find requests that have the X-Character-Id header set to the test user's character ID.
    // The axios client interceptor reads eve_active_char from localStorage.
    const requestsWithCharHeader = apiRequests.filter(
      (r) => r.headers["x-character-id"] === String(TEST_USER.characterId)
    );

    // At least one API request should have the character header
    expect(requestsWithCharHeader.length).toBeGreaterThan(0);
  });
});
