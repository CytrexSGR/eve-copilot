# Scheduler Service

Centralized job scheduling and background task management.

## Overview

Manages cron jobs and scheduled tasks using APScheduler.

**Port:** 8003

## Features

- **Job Scheduling** - Cron-based job scheduling
- **Job Management** - Start, stop, pause jobs via API
- **Job History** - Track job executions and results
- **Distributed Locking** - Redis-based job locking

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/scheduler/jobs` | GET | List all jobs |
| `POST /api/scheduler/jobs` | POST | Create new job |
| `GET /api/scheduler/jobs/{id}` | GET | Get job details |
| `DELETE /api/scheduler/jobs/{id}` | DELETE | Delete job |
| `POST /api/scheduler/jobs/{id}/pause` | POST | Pause job |
| `POST /api/scheduler/jobs/{id}/resume` | POST | Resume job |
| `POST /api/scheduler/jobs/{id}/trigger` | POST | Trigger job now |
| `GET /api/scheduler/jobs/{id}/history` | GET | Job execution history |
| `GET /health` | GET | Service health check |

## Default Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| `market_hot_items` | */4 min | Refresh hot item prices |
| `character_sync` | */30 min | Sync character data |
| `sov_tracker` | */30 min | Update sovereignty |
| `fw_tracker` | */30 min | Update faction warfare |
| `battle_cleanup` | */30 min | End stale battles |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_*` | Database connection | Yes |
| `REDIS_URL` | Redis (job store) | Yes |
| `JOB_STORE_TYPE` | `redis` or `memory` | `redis` |

## Database Tables

- `scheduler_jobs` - Job definitions
- `scheduler_job_history` - Execution history

## Local Development

```bash
cd services/scheduler-service
pip install -e ../../eve_shared
pip install -e .
uvicorn app.main:app --reload --port 8003
```
