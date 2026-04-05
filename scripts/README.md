# EVE Copilot — Scripts & Tests

## Test-Scripts

### `test-all.sh` — Pre-Deploy Test Runner
Führt alle Unit-Tests in allen Service-Containern aus.

```bash
./scripts/test-all.sh           # Kompakte Ausgabe
./scripts/test-all.sh --verbose  # Detaillierte Ausgabe
```

### `smoke-test.sh` — Post-Deploy Smoke Tests
Prüft Health-Endpoints, Auth-Flow und Business-Logik nach einem Deploy.

```bash
./scripts/smoke-test.sh
./scripts/smoke-test.sh --no-color  # Für Pipes/CI
```

### `install-hooks.sh` — Git Hook Installation
Installiert pre-push Hook der Tests vor dem Push ausführt.

```bash
./scripts/install-hooks.sh
```

## E2E Tests (Playwright)

```bash
cd e2e
npm install                       # Einmalig
npx playwright install chromium   # Einmalig
npx playwright test               # Alle E2E Tests
npx playwright test --headed      # Mit Browser-Fenster
npx playwright test --ui          # Interaktive UI
```

### Test-Journeys

| Test | Datei | Prüft |
|------|-------|-------|
| Login-Flow | `login.spec.ts` | Login-Prompt, Auth-State, Dashboard |
| Character-Management | `characters.spec.ts` | Character-Liste, Switcher, localStorage |
| Multi-Tab Sync | `multi-tab.spec.ts` | StorageEvent zwischen Tabs |
| Fingerprint-Dashboard | `fingerprints.spec.ts` | Daten laden, X-Character-Id Header |
| Ownership-Protection | `ownership.spec.ts` | 403/400 bei fremder/ungültiger ID |

## Typischer Workflow

```
1. Code ändern
2. git push              → Pre-Push Hook führt test-all.sh aus
3. Deploy:
   cd docker && git pull && docker compose build <service> && docker compose up -d <service>
4. ./scripts/smoke-test.sh    → Verifiziert Deployment
5. Bei größeren Änderungen:
   cd e2e && npx playwright test
```
