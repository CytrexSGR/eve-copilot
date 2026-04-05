import { test, expect } from "@playwright/test";
import { injectAuthCookie, TEST_USER } from "../helpers/auth";

test.describe("Multi-Tab Sync", () => {

  test("character change in tab A propagates to tab B via StorageEvent", async ({ context }) => {
    await injectAuthCookie(context);

    // Open two pages (tabs) in the same browser context
    const pageA = await context.newPage();
    const pageB = await context.newPage();

    await pageA.goto("/", { waitUntil: "domcontentloaded" });
    await pageB.goto("/", { waitUntil: "domcontentloaded" });

    // Wait for both pages to finish initial rendering
    await pageA.waitForTimeout(3000);
    await pageB.waitForTimeout(3000);

    // Set up a listener on page B to capture the storage event
    await pageB.evaluate(() => {
      (window as any).__storageEventFired = false;
      (window as any).__newCharId = null;
      window.addEventListener("storage", (e: StorageEvent) => {
        if (e.key === "eve_active_char") {
          (window as any).__storageEventFired = true;
          (window as any).__newCharId = e.newValue;
        }
      });
    });

    // Simulate a character switch in page A by changing localStorage
    const fakeCharId = 9999999;
    await pageA.evaluate((charId: number) => {
      localStorage.setItem("eve_active_char", String(charId));
    }, fakeCharId);

    // StorageEvent fires asynchronously in the other tab — wait a bit
    await pageB.waitForTimeout(1500);

    // Verify page B received the storage event
    const storageEventFired = await pageB.evaluate(() => (window as any).__storageEventFired);
    const newCharId = await pageB.evaluate(() => (window as any).__newCharId);

    expect(storageEventFired).toBe(true);
    expect(newCharId).toBe(String(fakeCharId));

    // Also verify localStorage is consistent across tabs
    const charFromB = await pageB.evaluate(() => localStorage.getItem("eve_active_char"));
    expect(charFromB).toBe(String(fakeCharId));

    await pageA.close();
    await pageB.close();
  });
});
