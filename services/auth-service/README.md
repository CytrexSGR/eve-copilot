# Auth Service

EVE SSO OAuth2 authentication, token management, and character management.

## Overview

Handles EVE Online Single Sign-On (SSO) authentication, token storage, refresh, tier subscriptions, ISK payments, and multi-character account management.

**Port:** 8010

## Features

- **EVE SSO OAuth2 + PKCE** - Complete OAuth2 flow with Proof Key for Code Exchange
- **Token Management** - Fernet-encrypted token storage and automatic refresh
- **Character Management** - Token health monitoring, primary switching, alt removal
- **Scope Tracking** - ESI scope consent tracking per character
- **Tier Subscriptions** - SaaS tier management with ISK payment processing
- **Platform Accounts** - Multi-character account linking (main + alts)
- **Org Management** - Corp member listing, role management, permission matrix, audit log (Phase 2)

## Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | GET | Initiate SSO login flow |
| `/api/auth/callback` | GET | OAuth2 callback handler |
| `/api/auth/public/login` | GET | Public SSO login |
| `/api/auth/public/callback` | GET | Public OAuth2 callback |
| `/api/auth/public/logout` | POST | Logout (clear session) |
| `/api/auth/public/account` | GET | Get account info |
| `/api/auth/public/me` | GET | Get current user info |
| `/api/auth/refresh/{id}` | POST | Refresh character token |
| `/api/auth/token/{id}` | GET | Get valid token (internal) |
| `/health` | GET | Service health check |

### Character Management (Phase 5)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/public/characters/{character_id}/token-health` | GET | Token health with scope groups |
| `/api/auth/public/account/primary/{character_id}` | PUT | Switch primary character |
| `/api/auth/public/account/characters/{character_id}` | DELETE | Remove alt character |

### Org Management (Phase 2)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/public/org/overview` | GET | Corp overview (member count, roles, recent activity) |
| `/api/auth/public/org/members` | GET | List corp members with roles and join dates |
| `/api/auth/public/org/members/{character_id}/role` | PUT | Update member role (member/officer/director/admin) |
| `/api/auth/public/org/members/{character_id}` | DELETE | Remove member from corp |
| `/api/auth/public/org/permissions` | GET | Get role permission matrix |
| `/api/auth/public/org/permissions` | PUT | Update role permissions |
| `/api/auth/public/org/audit` | GET | Query audit log (filterable by actor/action/date) |
| `/api/auth/public/org/audit/export` | GET | Export audit log as CSV |

### Tier & Subscription

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tier/resolve` | GET | Resolve effective tier |
| `/api/tier/payment/initiate` | POST | Initiate ISK payment |
| `/api/tier/payment/status/{code}` | GET | Check payment status |
| `/api/settings/*` | GET/PUT | User settings |

## Token Health Response

```json
{
  "character_id": 1117367444,
  "character_name": "Cytrex",
  "is_valid": true,
  "status": "valid",
  "scopes": ["esi-skills.read_skills.v1", "..."],
  "missing_scopes": [],
  "scope_groups": {
    "Skills": "full",
    "Wallet": "full",
    "Assets": "full",
    "Industry": "full",
    "Location": "full"
  },
  "expires_in_hours": 720,
  "last_refresh": "2026-02-20T21:54:37Z"
}
```

**Scope Groups (13 categories):** Skills, Wallet, Assets, Industry, Fittings, Location, Contacts, Contracts, Mail, Clones, Blueprints, Killmails, Corp Roles

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ESI_CLIENT_ID` | EVE application client ID | Yes |
| `ESI_CLIENT_SECRET` | EVE application secret | Yes |
| `ESI_CALLBACK_URL` | OAuth callback URL | Yes |
| `POSTGRES_*` | Database connection | Yes |
| `REDIS_URL` | Redis connection | Yes |
| `FERNET_KEY` | Token encryption key | Yes |

## Database Tables

- `platform_accounts` - Account data (id, primary_character_id, tier, corp/alliance)
- `account_characters` - Character-to-account linking (account_id, character_id, is_primary)
- `character_tokens` - OAuth tokens (Fernet-encrypted)
- `character_scope_consents` - ESI scope tracking per character (granted/requested scopes)
- `tier_subscriptions` - SaaS subscriptions
- `tier_payments` - ISK payment records
- `org_permissions` - Role-based permission matrix (role → permissions mapping)
- `org_audit_log` - Audit trail for org management actions (role changes, kicks, permission updates)

## Router Structure

```
app/routers/
├── auth.py                  # Internal SSO + token management
├── public_auth.py           # Public login/callback/logout
├── character_management.py  # Token health, primary switch, alt removal (Phase 5)
├── tier.py                  # Tier resolution, ISK payments
├── subscription.py          # Subscription CRUD
├── admin.py                 # Admin operations
└── settings.py              # User settings
```

## Local Development

```bash
cd services/auth-service
pip install -e ../../eve_shared
pip install -e .
uvicorn app.main:app --reload --port 8010
```

## EVE Developer Portal

Register your application at https://developers.eveonline.com/

Required scopes are listed in [CLAUDE.esi.md](../../CLAUDE.esi.md).
