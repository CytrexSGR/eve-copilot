# Finance Service (Port 8016)

Corporation financial operations microservice.

## Routers

| Router | Endpoints | Purpose |
|--------|-----------|---------|
| wallet.py | 6 | Corp wallet journal sync, balance tracking |
| mining.py | 5 | Mining tax calculation, observer dashboard, extraction calendar |
| invoices.py | 4 | Invoice generation and management |
| reports.py | 3 | Financial reports |
| srp.py | 12 | SRP claims, doctrine CRUD, pricing, clone, changelog |
| buyback.py | 3 | Buyback program with Janice API |

## Doctrine Management Extensions

### New Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/finance/doctrine/{id}/clone` | Clone a doctrine with new name |
| GET | `/api/finance/doctrine/{id}/price` | Auto-calculate doctrine price from Jita market |
| GET | `/api/finance/doctrine/{id}/changelog` | Get changelog entries for a doctrine |
| GET | `/api/finance/corp/{corp_id}/changelog` | Get changelog entries for all corp doctrines |

### Database Tables

| Table | Purpose |
|-------|---------|
| fleet_doctrines | Doctrine definitions (name, fitting, ship_type_id, category, etc.) |
| doctrine_changelog | Audit log for doctrine changes (created, updated, cloned, deleted) |
| srp_claims | SRP claim tracking with killmail matching |
| srp_payouts | SRP payout records |

### Key Columns

- **fleet_doctrines.category** — Categorization field (e.g., "Mainline DPS", "Logistics", "Tackle")
- **doctrine_changelog.action** — One of: created, updated, cloned, deleted
- **doctrine_changelog.changes** — JSONB diff of what changed

## Features

- Wallet journal sync from ESI
- Mining tax calculation (observer-based)
- Moon mining dashboard (extraction calendar, structure performance, ore analytics)
- Invoice generation
- SRP claims with killmail matching + doctrine pricing (fuzzy + Dogma compliance)
- Doctrine CRUD with EFT/DNA import
- Doctrine cloning with changelog
- Auto-pricing from Jita market data
- Doctrine changelog (audit trail)
- Buyback contracts (Janice API integration)
