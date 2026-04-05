import { BrowserContext, Page } from "@playwright/test";
import jwt from "jsonwebtoken";

const JWT_SECRET = "8bGKMxz1NMDxDTXrjuXZ90ahVKTM7vp-XSbJXmoe9L0";

export const TEST_USER = {
  characterId: 1117367444,
  secondaryCharacterId: 110592475,
  accountId: 2,
  characterName: "Cytrex",
  secondaryCharacterName: "Cytricia",
} as const;

/**
 * Creates a valid JWT token for the test user.
 */
export function createTestToken(): string {
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    sub: String(TEST_USER.characterId),
    account_id: TEST_USER.accountId,
    name: TEST_USER.characterName,
    character_ids: [TEST_USER.characterId, TEST_USER.secondaryCharacterId],
    type: "public_session",
    iat: now,
    exp: now + 3600, // 1 hour
  };
  return jwt.sign(payload, JWT_SECRET, { algorithm: "HS256" });
}

/**
 * Injects auth cookie + localStorage init script into the browser context.
 * The init script runs BEFORE any page JavaScript, ensuring localStorage
 * flags are present when AuthContext first checks them.
 *
 * Call this ONCE per context before navigating to any authenticated page.
 */
export async function injectAuthCookie(context: BrowserContext): Promise<void> {
  const token = createTestToken();

  // Set the session cookie on localhost
  await context.addCookies([
    {
      name: "session",
      value: token,
      domain: "localhost",
      path: "/",
      httpOnly: false,
      secure: false,
      sameSite: "Lax",
    },
  ]);

  // addInitScript runs before ANY page JavaScript on every new page load.
  // This ensures localStorage is set before React's AuthContext reads it.
  await context.addInitScript((charId: number) => {
    localStorage.setItem("eve_auth", "1");
    localStorage.setItem("eve_active_char", String(charId));
  }, TEST_USER.characterId);
}
