"""Doctrine Engine — bridge between Finance doctrine definitions and the Dogma Engine.

Normalizes fleet_doctrines JSONB into FittingStatsRequest, delegates to
FittingStatsService for Dogma-powered stats, and adds readiness/compliance/BOM.
"""

import json
import logging
from typing import Optional, List

from app.services.fitting_service import FittingItem
from app.services.fitting_stats import FittingStatsService
from app.services.fitting_stats.models import FittingStatsRequest
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Flag ranges per slot type (matching finance-service doctrine.py)
SLOT_FLAG_RANGES = {
    "high": range(27, 35),   # 27-34
    "med":  range(19, 27),   # 19-26
    "low":  range(11, 19),   # 11-18
    "rig":  range(92, 100),  # 92-99
}


def normalize_doctrine_to_request(doctrine: dict) -> FittingStatsRequest:
    """Convert Finance JSONB doctrine to a FittingStatsRequest.

    Expands quantity into individual FittingItems with sequential flags.
    Drones stay grouped with flag=87 (processed separately by FittingStatsService).
    """
    fitting = doctrine["fitting_json"]
    items: list[FittingItem] = []

    for slot_name, flag_range in SLOT_FLAG_RANGES.items():
        slot_idx = 0
        for entry in fitting.get(slot_name, []):
            for _ in range(entry["quantity"]):
                if slot_idx < len(flag_range):
                    items.append(FittingItem(
                        type_id=entry["type_id"],
                        flag=flag_range[slot_idx],
                        quantity=1,
                    ))
                    slot_idx += 1

    for drone in fitting.get("drones", []):
        items.append(FittingItem(
            type_id=drone["type_id"],
            flag=87,
            quantity=drone["quantity"],
        ))

    return FittingStatsRequest(
        ship_type_id=doctrine["ship_type_id"],
        items=items,
    )


class DoctrineEngine:
    """Thin orchestrator bridging Finance doctrines to the Dogma Engine.

    Reads fleet_doctrines from shared DB, normalizes to FittingStatsRequest,
    delegates to FittingStatsService, caches results.
    """

    CACHE_TTL_ALL_V = 3600      # 1 hour for All V stats
    CACHE_TTL_CHARACTER = 900   # 15 minutes for character stats

    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis
        self.fitting_stats = FittingStatsService(db, redis)

    def _cache_key(self, doctrine_id: int, character_id: Optional[int]) -> str:
        suffix = str(character_id) if character_id else "all_v"
        return f"doctrine-stats:{doctrine_id}:{suffix}"

    def _get_cached(self, key: str):
        if not self.redis:
            return None
        try:
            data = self.redis.get(key)
            if data:
                from app.services.fitting_stats.models import FittingStatsResponse
                return FittingStatsResponse.model_validate_json(data)
        except Exception as e:
            logger.warning("Cache get failed for %s: %s", key, e)
        return None

    def _set_cached(self, key: str, value, ttl: int):
        if not self.redis:
            return
        try:
            self.redis.set(key, value.model_dump_json(), ex=ttl)
        except Exception as e:
            logger.warning("Cache set failed for %s: %s", key, e)

    def _get_doctrine(self, doctrine_id: int) -> Optional[dict]:
        """Read a single doctrine from fleet_doctrines."""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT d.id, d.corporation_id, d.name, d.ship_type_id,
                       d.fitting_json, d.is_active, d.base_payout,
                       t."typeName" as ship_name
                FROM fleet_doctrines d
                LEFT JOIN "invTypes" t ON t."typeID" = d.ship_type_id
                WHERE d.id = %s
            """, (doctrine_id,))
            row = cur.fetchone()

        if not row:
            return None

        # Parse fitting_json if stored as string
        fj = row["fitting_json"]
        if isinstance(fj, str):
            fj = json.loads(fj)

        return {**row, "fitting_json": fj}

    def calculate_doctrine_stats(
        self,
        doctrine_id: int,
        character_id: Optional[int] = None,
    ):
        """Calculate full Dogma stats for a doctrine fitting.

        Results are cached in Redis (1h All V, 15min character).
        """
        cache_key = self._cache_key(doctrine_id, character_id)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        doctrine = self._get_doctrine(doctrine_id)
        if not doctrine:
            raise ValueError(f"Doctrine {doctrine_id} not found")

        req = normalize_doctrine_to_request(doctrine)
        if character_id:
            req.character_id = character_id

        result = self.fitting_stats.calculate_stats(req)

        ttl = self.CACHE_TTL_CHARACTER if character_id else self.CACHE_TTL_ALL_V
        self._set_cached(cache_key, result, ttl)

        return result

    def check_readiness(self, doctrine_id: int, character_id: int) -> dict:
        """Compare All-V stats vs character stats for a doctrine.

        Returns readiness dict with ratios, missing skills, and can_fly flag.
        """
        doctrine = self._get_doctrine(doctrine_id)
        if not doctrine:
            raise ValueError(f"Doctrine {doctrine_id} not found")

        req = normalize_doctrine_to_request(doctrine)

        # All V baseline
        req_allv = req.model_copy()
        req_allv.character_id = None
        stats_allv = self.fitting_stats.calculate_stats(req_allv)

        # Character actual
        req_char = req.model_copy()
        req_char.character_id = character_id
        stats_char = self.fitting_stats.calculate_stats(req_char)

        missing_skills = [
            s for s in stats_char.required_skills
            if s.trained_level is not None and s.trained_level < s.required_level
        ]

        return {
            "doctrine_id": doctrine_id,
            "character_id": character_id,
            "all_v_stats": stats_allv,
            "character_stats": stats_char,
            "dps_ratio": round(
                stats_char.offense.total_dps / max(stats_allv.offense.total_dps, 1), 3
            ),
            "ehp_ratio": round(
                stats_char.defense.total_ehp / max(stats_allv.defense.total_ehp, 1), 3
            ),
            "missing_skills": missing_skills,
            "can_fly": len(missing_skills) == 0 and all(
                s.trained_level is not None and s.trained_level >= s.required_level
                for s in stats_char.required_skills
            ),
        }

    # Compliance scoring weights
    WEIGHT_DPS = 0.35
    WEIGHT_EHP = 0.35
    WEIGHT_TANK = 0.15
    WEIGHT_CAP = 0.15

    def check_compliance(self, doctrine_id: int, killmail_items: list) -> dict:
        """Stats-based killmail compliance scoring against a doctrine.

        Score: 35% DPS + 35% EHP + 15% tank type + 15% cap stability, capped at 1.0.
        """
        doctrine = self._get_doctrine(doctrine_id)
        if not doctrine:
            raise ValueError(f"Doctrine {doctrine_id} not found")

        # Doctrine stats
        req_doctrine = normalize_doctrine_to_request(doctrine)
        doctrine_stats = self.fitting_stats.calculate_stats(req_doctrine)

        # Killmail stats
        km_req = FittingStatsRequest(
            ship_type_id=doctrine["ship_type_id"],
            items=[
                FittingItem(type_id=i["type_id"], flag=i["flag"], quantity=1)
                for i in killmail_items
            ],
        )
        km_stats = self.fitting_stats.calculate_stats(km_req)

        dps_ratio = km_stats.offense.total_dps / max(doctrine_stats.offense.total_dps, 1)
        ehp_ratio = km_stats.defense.total_ehp / max(doctrine_stats.defense.total_ehp, 1)
        tank_match = km_stats.defense.tank_type == doctrine_stats.defense.tank_type
        cap_match = km_stats.capacitor.stable == doctrine_stats.capacitor.stable

        score = (
            min(dps_ratio, 1.0) * self.WEIGHT_DPS
            + min(ehp_ratio, 1.0) * self.WEIGHT_EHP
            + (1.0 if tank_match else 0.5) * self.WEIGHT_TANK
            + (1.0 if cap_match else 0.7) * self.WEIGHT_CAP
        )
        score = min(score, 1.0)

        return {
            "doctrine_id": doctrine_id,
            "compliance_score": round(score, 3),
            "dps_ratio": round(min(dps_ratio, 9.99), 3),
            "ehp_ratio": round(min(ehp_ratio, 9.99), 3),
            "tank_match": tank_match,
            "cap_match": cap_match,
        }

    def generate_bom(self, doctrine_id: int, quantity: int = 1) -> list:
        """Generate Bill of Materials for a doctrine × fleet size.

        Returns list of {type_id, type_name, quantity} sorted by name.
        """
        doctrine = self._get_doctrine(doctrine_id)
        if not doctrine:
            raise ValueError(f"Doctrine {doctrine_id} not found")

        fitting = doctrine["fitting_json"]
        bom: dict[int, dict] = {}

        # Ship hull
        ship_tid = doctrine["ship_type_id"]
        bom[ship_tid] = {
            "type_id": ship_tid,
            "type_name": doctrine.get("ship_name") or "",
            "quantity": quantity,
        }

        # All fitted modules + drones
        for slot_name in ("high", "med", "low", "rig", "drones"):
            for entry in fitting.get(slot_name, []):
                tid = entry["type_id"]
                if tid in bom:
                    bom[tid]["quantity"] += entry["quantity"] * quantity
                else:
                    bom[tid] = {
                        "type_id": tid,
                        "type_name": entry.get("type_name", ""),
                        "quantity": entry["quantity"] * quantity,
                    }

        return sorted(bom.values(), key=lambda x: x["type_name"])
