# EVE Co-Pilot - Development Guide

> **Detailed Guides:** [Backend](04_BACKEND_GUIDE.md) | [Frontend](05_FRONTEND_GUIDE.md)
>
> **Last Updated:** 2026-02-26

---

## Mission

We build the **total dominance engine** for New Eden. Economic warfare, intelligence operations, strategic conquest.

**Philosophy:** Information asymmetry is wealth. Automation is power. Vertical integration is victory.

---

## Credentials

| What | Value |
|------|-------|
| Sudo | `<SUDO_PASSWORD>` |
| Database | `eve_sde` / `eve` / `<DB_PASSWORD>` |
| GitHub Token | `/home/cytrex/Userdocs/.env` (GITHUB_TOKEN) |
| EVE SSO | Client ID: `<EVE_CLIENT_ID>` |

---

## Quick Start

```bash
# Start all services (Docker)
cd /home/cytrex/eve_copilot/docker
docker compose up -d
docker compose ps                  # Verify all services healthy

# Frontend development (fast HMR mode)
cd /home/cytrex/eve_copilot/public-frontend
./dev.sh                           # Vite dev server on port 5175

# Database access
echo '<SUDO_PASSWORD>' | sudo -S docker exec eve_db psql -U eve -d eve_sde

# Run unit tests (any service)
cd /home/cytrex/eve_copilot/services/<service-name>
python3 -m pytest app/tests/ -v --override-ini="addopts="
```

**Access Points:**
- API Gateway: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Public Frontend (Dev HMR): http://localhost:5175
- Public Frontend (Prod): http://localhost:5173
- ectmap (Universe Map): http://localhost:3001

---

## Production

| Service | Value |
|---------|-------|
| **Domain** | `eve.infinimind-creations.com` |
| **Server IP** | `your-server-ip` |
| **Cloudflare** | Active (Proxied, Full Strict SSL) |
| **Nameservers** | `kristina.ns.cloudflare.com`, `rocco.ns.cloudflare.com` |
| **Registrar** | all-inkl (KAS) |
| **VM** | Proxmox VM 100 |

### Security Layers

| Layer | Protection |
|-------|------------|
| **Cloudflare** | WAF, Bot Fight Mode, Rate Limit (100 req/10s for `/api/`) |
| **Nginx** | Blocks non-Cloudflare IPs, allows LAN (`cloudflare-allow.conf`) |
| **Waiting Room** | Max 50 conn (server), 30 conn (per IP) |

### API Routing (nginx)

| Path | Target |
|------|--------|
| `/api/*` | api-gateway (:8000) → routes to microservices |
| `/ectmap` | ectmap (:3001) |
| `/` | public-frontend (:5173) |

### Operations

```bash
# Docker management
cd /home/cytrex/eve_copilot/docker
docker compose ps                  # Check service health
docker compose logs -f <service>   # View logs
docker compose restart <service>   # Restart a service
docker compose build --no-cache <service> && docker compose up -d <service>  # Rebuild

# Database
echo '<SUDO_PASSWORD>' | sudo -S docker exec eve_db psql -U eve -d eve_sde

# Run migration
cat migrations/XXX.sql | sudo -S docker exec -i eve_db psql -U eve -d eve_sde
```

---

## Language Policy

- **Chat:** German
- **Code, Docs, Commits:** English
- **UI Text:** English

---

## Core Principles

1. **NICHT RATEN. NACHSCHAUEN!** - Don't assume, verify.
2. **Do it right the first time** - Shortcuts create more work later.
3. **Parallel over sequential** - Multiple tool calls in one message = 3x faster.

---

## Git - MANDATORY

**Repo:** https://github.com/CytrexSGR/Eve-Online-Copilot

After every code change:
```bash
git add -A && git commit -m "type: description" && git push origin main
```

**Commit Format:**
```
type: Short description

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

---

## Key Services & Ports

| Port | Service | Purpose |
|------|---------|---------|
| 8000 | api-gateway | Main API entry point |
| 8002 | war-intel-service | Combat intelligence, battles, reports |
| 8003 | scheduler-service | Cron jobs (40+ jobs) |
| 8004 | market-service | Market prices, arbitrage |
| 8005 | production-service | Manufacturing, PI |
| 8006 | shopping-service | Shopping lists, transport |
| 8007 | character-service | Characters, skills, Dogma engine |
| 8008 | mcp-service | 609 dynamic MCP tools |
| 8010 | auth-service | EVE SSO OAuth |
| 8011 | ectmap-service | Map data |
| 8012 | wormhole-service | J-Space intelligence |
| 8013 | zkillboard | Live kill stream |
| 8014 | dotlan-service | DOTLAN scraping |
| 8015 | hr-service | HR, vetting |
| 8016 | finance-service | SRP, doctrines |
| 8017 | military-service | D-Scan, fleet PAPs |
| 5173 | public-frontend | Public dashboard (nginx) |
| 3001 | ectmap | Universe map (Next.js) |

---

## Navigation

| Need | Location |
|------|----------|
| **System Architecture** | [03_ARCHITECTURE.md](03_ARCHITECTURE.md) |
| **Backend: DB, API, Services** | [04_BACKEND_GUIDE.md](04_BACKEND_GUIDE.md) |
| **Frontend: React, Components** | [05_FRONTEND_GUIDE.md](05_FRONTEND_GUIDE.md) |
| **Implementation Plans** | `docs/plans/` |
| **Live API Documentation** | http://localhost:8000/docs |

---

## Quick Reference

| Task | Command |
|------|---------|
| Start all services | `cd docker && docker compose up -d` |
| Check health | `docker compose ps` |
| View logs | `docker compose logs -f <service>` |
| Connect to DB | `sudo -S docker exec eve_db psql -U eve -d eve_sde` |
| Run migration | `cat migrations/XXX.sql \| sudo -S docker exec -i eve_db psql -U eve -d eve_sde` |
| Run tests | `cd services/<name> && python3 -m pytest app/tests/ -v --override-ini="addopts="` |
| Check ESI status | https://esi.evetech.net/status.json |
| Frontend dev | `cd public-frontend && ./dev.sh` |
