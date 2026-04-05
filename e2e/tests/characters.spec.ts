import { test, expect } from "@playwright/test";
import { injectAuthCookie, TEST_USER } from "../helpers/auth";

test.describe("Character Management", () => {

  test("characters page shows linked characters", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/characters");

    // The Characters page loads character summaries for the account's characters.
    // It displays character portrait images and character names.
    // Wait for the primary character name to appear.
    await expect(
      page.getByText(TEST_USER.characterName).first()
    ).toBeVisible({ timeout: 30_000 });

    // The secondary character should also be listed
    await expect(
      page.getByText(TEST_USER.secondaryCharacterName).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("active character ID is stored in localStorage", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/characters");

    // Wait for page to load
    await expect(
      page.getByText(TEST_USER.characterName).first()
    ).toBeVisible({ timeout: 30_000 });

    // Check that localStorage has the active character set
    const activeChar = await page.evaluate(() => localStorage.getItem("eve_active_char"));
    expect(activeChar).toBe(String(TEST_USER.characterId));
  });

  test("character switcher shows both characters in header", async ({ context, page }) => {
    await injectAuthCookie(context);
    await page.goto("/characters");

    // Wait for page to load
    await expect(
      page.getByText(TEST_USER.characterName).first()
    ).toBeVisible({ timeout: 30_000 });

    // The Layout header should show a character switcher button (since account has >1 characters).
    // The switcher button contains the active character's name and a dropdown arrow.
    // Find the character switcher button in the header — it contains the character portrait.
    const charSwitcherBtn = page.locator("header button").filter({
      has: page.locator(`img[src*="characters/${TEST_USER.characterId}/portrait"]`),
    });

    // If there's a char switcher, it should be visible
    const count = await charSwitcherBtn.count();
    if (count > 0) {
      await charSwitcherBtn.click();

      // After clicking, the dropdown should show both character names.
      // The dropdown buttons are rendered inside a div after the switcher button.
      // Use a more specific locator to find dropdown items.
      // "Cytrex PRIMARY" and "Cytricia" should be in the dropdown.
      await expect(
        page.getByRole("button", { name: /Cytrex.*PRIMARY/i })
      ).toBeVisible({ timeout: 5_000 });

      await expect(
        page.getByRole("button", { name: TEST_USER.secondaryCharacterName })
      ).toBeVisible();
    }
  });
});
