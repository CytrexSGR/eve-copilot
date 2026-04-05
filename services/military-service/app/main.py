"""Military Service — Fleet Operations, D-Scan, Local Scan, Ops Calendar."""
import logging
import os
import glob as glob_module
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

app = FastAPI(
    title="EVE Military Service",
    description="Fleet operations, D-Scan analysis, ops calendar, fleet sync",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "military-service"}

@app.on_event("startup")
async def startup():
    """Run migrations and initialize connections."""
    from app.database import get_db

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
            for filepath in sorted(glob_module.glob(os.path.join(migration_dir, "*.sql"))):
                filename = os.path.basename(filepath)
                cur.execute("SELECT 1 FROM _migrations WHERE filename = %s", (filename,))
                if not cur.fetchone():
                    with open(filepath) as f:
                        cur.execute(f.read())
                    cur.execute("INSERT INTO _migrations (filename) VALUES (%s)", (filename,))
                    logger.info(f"Applied migration: {filename}")
    finally:
        conn.close()

    # Start the reminder scheduler
    async def check_op_reminders():
        """Check for ops starting in <=30min, send reminders."""
        try:
            from app.services.discord import notify_event
            from app.database import db_cursor as _db_cursor
            with _db_cursor() as cur:
                cur.execute("""
                    SELECT * FROM scheduled_operations
                    WHERE is_cancelled = FALSE
                      AND formup_time BETWEEN NOW() AND NOW() + INTERVAL '30 minutes'
                      AND fleet_operation_id IS NULL
                """)
                ops = cur.fetchall()
            for op in ops:
                embed = {
                    "title": f"Formup in 30min: {op['title']}",
                    "color": 0xFF9800,
                    "fields": [
                        {"name": "FC", "value": op["fc_name"], "inline": True},
                        {"name": "System", "value": op.get("formup_system") or "TBD", "inline": True},
                        {"name": "Time", "value": str(op["formup_time"]), "inline": True},
                    ],
                }
                await notify_event("op_reminder", op["id"], op["corporation_id"], embed)
            if ops:
                logger.info("Checked %d upcoming ops for reminders", len(ops))
        except Exception:
            logger.warning("Op reminder check failed", exc_info=True)

    scheduler.add_job(check_op_reminders, "interval", minutes=5)
    scheduler.start()
    logger.info("Op reminder scheduler started (every 5 minutes)")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.routers import fleet_ops, fleet_comp, dscan, local_scan, discord_relay

app.include_router(fleet_ops.router, prefix="/api/military", tags=["Fleet Operations"])
app.include_router(fleet_comp.router, prefix="/api/fleet", tags=["Fleet Composition"])
app.include_router(dscan.router, prefix="/api/military", tags=["D-Scan"])
app.include_router(local_scan.router, prefix="/api/military", tags=["Local Scan"])
app.include_router(discord_relay.router, prefix="/api/military", tags=["Discord Relay"])

# Incursions Tracker (ESI Public)
from app.routers import incursions
from app.routers import ops_calendar
app.include_router(incursions.router, prefix="/api/military", tags=["Incursions"])
app.include_router(ops_calendar.router, prefix="/api/military", tags=["Ops Calendar"])

# Notification Config (Discord fleet notifications)
from app.routers import notifications
app.include_router(notifications.router, prefix="/api/military", tags=["Notifications"])

# Fleet Sync (ESI live polling)
from app.routers import fleet_sync
app.include_router(fleet_sync.router, prefix="/api/military", tags=["Fleet Sync"])

# Pilot Activity Dashboard
from app.routers import pilot_activity
app.include_router(pilot_activity.router, prefix="/api/military", tags=["Pilot Activity"])
