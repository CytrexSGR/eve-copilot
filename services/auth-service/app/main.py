"""EVE Auth Service - Handles EVE SSO authentication."""

import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eve_shared import setup_logging, get_db, get_redis, health_router
from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.middleware.exception_handler import register_exception_handlers
from eve_shared.metrics_router import metrics_router
from eve_shared.metrics import service_info
from app.config import settings
from app.routers import auth, settings as settings_router
from app.routers.public_auth import router as public_auth_router
from app.routers.subscription import router as subscription_router
from app.routers.admin import router as admin_router
from app.routers.tier import router as tier_router
from app.routers.character_management import router as char_mgmt_router
from app.routers.org_management import router as org_mgmt_router
from app.routers.diplomacy import router as diplomacy_router
from app.routers.bulletin import router as bulletin_router


def _migrate_tokens_from_json():
    """One-time migration: import tokens from JSON file into PostgreSQL.

    Runs at startup. Only imports if the oauth_tokens table is empty
    and the JSON token file exists with data.
    """
    logger = logging.getLogger(__name__)

    from app.database import db_cursor
    from app.repository.db_token_store import DatabaseTokenStore
    from app.models.token import StoredToken

    # Check if DB already has tokens
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM oauth_tokens")
        count = cur.fetchone()["cnt"]

    if count > 0:
        logger.info(f"Token DB already has {count} characters, skipping JSON migration")
        return

    # Check if JSON file exists
    token_file = Path(settings.token_file)
    if not token_file.exists():
        logger.info("No JSON token file found, nothing to migrate")
        return

    try:
        with open(token_file) as f:
            tokens_data = json.load(f)
    except Exception as e:
        logger.warning(f"Could not read JSON token file: {e}")
        return

    if not tokens_data:
        return

    store = DatabaseTokenStore()
    migrated = 0
    for char_id_str, data in tokens_data.items():
        try:
            # Parse expires_at from various formats
            expires_at = data.get("expires_at")
            if isinstance(expires_at, (int, float)):
                expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)
            elif isinstance(expires_at, str):
                dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                expires_at = dt

            updated_at = data.get("updated_at")
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
            else:
                updated_at = datetime.now(timezone.utc)

            token = StoredToken(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                expires_at=expires_at,
                character_id=data["character_id"],
                character_name=data["character_name"],
                scopes=data.get("scopes", []),
                updated_at=updated_at,
            )
            store.save_token(data["character_id"], token)
            migrated += 1
            logger.info(f"  Migrated: {data['character_name']} ({data['character_id']})")
        except Exception as e:
            logger.warning(f"  Failed to migrate {char_id_str}: {e}")

    logger.info(f"Token migration complete: {migrated}/{len(tokens_data)} characters imported from JSON to PostgreSQL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger = setup_logging(settings.service_name, settings.log_level)
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")

    get_db().initialize()
    get_redis().initialize()

    # Migrate tokens from JSON file to DB (one-time, if DB is empty)
    _migrate_tokens_from_json()

    yield

    # Shutdown
    get_db().close()
    get_redis().close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="EVE Auth Service",
    description="EVE Online SSO Authentication Service with PKCE",
    version=settings.service_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_middleware(MetricsMiddleware, service_name=settings.service_name
)

register_exception_handlers(app)

# Routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(public_auth_router, prefix="/api/auth")
app.include_router(subscription_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(tier_router, prefix="/api")
app.include_router(char_mgmt_router, prefix="/api/auth")
app.include_router(org_mgmt_router, prefix="/api/auth")
app.include_router(diplomacy_router, prefix="/api/auth", tags=["Diplomacy"])
app.include_router(bulletin_router, prefix="/api/auth", tags=["Bulletin"])
