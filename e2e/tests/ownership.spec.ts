import { test, expect } from "@playwright/test";
import { createTestToken, TEST_USER } from "../helpers/auth";

/**
 * Ownership Protection tests.
 *
 * The CharacterContextMiddleware in the API gateway validates the
 * X-Character-Id header against the JWT's character_ids claim.
 *
 * - Foreign character ID (not in JWT) => 403
 * - Own character ID (in JWT) => 200 (or non-401/403)
 * - Non-numeric character ID => 400
 *
 * We make direct API calls via page.request to test this,
 * using the session cookie from the JWT.
 */

test.describe("Ownership Protection", () => {

  test("foreign character ID returns 403", async ({ request }) => {
    const token = createTestToken();

    // Use a character ID that does NOT belong to the test user
    const foreignCharId = 9999999999;

    const response = await request.get("http://localhost:5173/api/character/summary/all", {
      headers: {
        "Cookie": `session=${token}`,
        "X-Character-Id": String(foreignCharId),
      },
    });

    expect(response.status()).toBe(403);

    const body = await response.json();
    expect(body.error).toBe("character_not_linked");
  });

  test("own character ID returns non-401/403", async ({ request }) => {
    const token = createTestToken();

    const response = await request.get("http://localhost:5173/api/character/summary/all", {
      headers: {
        "Cookie": `session=${token}`,
        "X-Character-Id": String(TEST_USER.characterId),
      },
    });

    // Should NOT be 401 or 403 — the ownership check itself should pass
    expect(response.status()).not.toBe(401);
    expect(response.status()).not.toBe(403);
  });

  test("non-numeric character ID returns 400", async ({ request }) => {
    const token = createTestToken();

    const response = await request.get("http://localhost:5173/api/character/summary/all", {
      headers: {
        "Cookie": `session=${token}`,
        "X-Character-Id": "not-a-number",
      },
    });

    expect(response.status()).toBe(400);

    const body = await response.json();
    expect(body.error).toBe("invalid_character_id");
  });
});
