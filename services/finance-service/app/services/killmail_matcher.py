"""Killmail Matching Engine for SRP validation.

Compares a killmail fitting against a fleet doctrine using fuzzy matching:
1. Exact type_id match → "exact"
2. Same group_id + lower meta-level → "downgrade"
3. Same group_id + higher meta-level → "upgrade" (payout capped)
4. Abyssal module → "review_required"
5. Missing module → "missing"
"""

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Optional

import httpx
from eve_shared import get_db
from eve_shared.esi import EsiClient

from app.config import settings

logger = logging.getLogger(__name__)

# ESI flag-to-slot mapping
FLAG_SLOT_MAP = {}
for f in range(11, 19):
    FLAG_SLOT_MAP[f] = "low"
for f in range(19, 27):
    FLAG_SLOT_MAP[f] = "med"
for f in range(27, 35):
    FLAG_SLOT_MAP[f] = "high"
for f in range(92, 100):
    FLAG_SLOT_MAP[f] = "rig"
FLAG_SLOT_MAP[87] = "drones"

# SDE attribute ID for meta-level
ATTR_META_LEVEL = 633

# Abyssal type_id range (mutated modules)
ABYSSAL_MIN_TYPE_ID = 47700


class KillmailMatcher:
    """Matches killmail fittings against fleet doctrines."""

    def __init__(self):
        self.db = get_db()
        self.esi = EsiClient()

    async def fetch_killmail(
        self, killmail_id: int, killmail_hash: str
    ) -> Optional[dict]:
        """Fetch killmail from ESI.

        Returns the full killmail data including victim items.
        """
        try:
            data = await self.esi.get(
                f"/killmails/{killmail_id}/{killmail_hash}/",
            )
            return data
        except Exception as e:
            logger.error("Failed to fetch killmail %s: %s", killmail_id, e)
            return None

    def parse_killmail_items(self, items: list[dict]) -> dict:
        """Parse killmail items into slot-grouped structure.

        ESI killmail items have: flag, item_type_id, quantity_destroyed,
        quantity_dropped, singleton.

        Returns: {"high": [...], "med": [...], "low": [...], "rig": [...],
                  "drones": [...], "cargo": [...]}
        """
        result = defaultdict(list)

        for item in items:
            flag = item.get("flag", 0)
            type_id = item.get("item_type_id", 0)
            qty_destroyed = item.get("quantity_destroyed", 0)
            qty_dropped = item.get("quantity_dropped", 0)
            total_qty = qty_destroyed + qty_dropped

            if total_qty == 0:
                continue

            slot = FLAG_SLOT_MAP.get(flag)
            if not slot:
                # Cargo, fighter bay, etc. — skip for matching
                continue

            result[slot].append({
                "type_id": type_id,
                "quantity": total_qty,
            })

        return dict(result)

    def match_fitting(
        self, killmail_items: dict, doctrine_fitting: dict
    ) -> dict:
        """Compare killmail fitting against doctrine fitting.

        Returns match result with categorized items and a match score.
        """
        result = {
            "exact": [],
            "downgrades": [],
            "upgrades": [],
            "missing": [],
            "review_required": [],
            "extra": [],
        }

        for slot in ("high", "med", "low", "rig"):
            doctrine_mods = doctrine_fitting.get(slot, [])
            killmail_mods = killmail_items.get(slot, [])

            slot_result = self._match_slot(doctrine_mods, killmail_mods, slot)
            for category in result:
                result[category].extend(slot_result.get(category, []))

        # Drones: match by type_id only (no slot position)
        doctrine_drones = doctrine_fitting.get("drones", [])
        killmail_drones = killmail_items.get("drones", [])
        drone_result = self._match_drones(doctrine_drones, killmail_drones)
        for category in result:
            result[category].extend(drone_result.get(category, []))

        # Calculate match score
        result["match_score"] = self._calculate_match_score(result)

        return result

    def _match_slot(
        self, doctrine_mods: list, killmail_mods: list, slot: str
    ) -> dict:
        """Match modules in a single slot type.

        For each doctrine module, find the best matching killmail module.
        """
        result = defaultdict(list)

        # Build a pool of available killmail items
        km_pool: list[dict] = []
        for mod in killmail_mods:
            for _ in range(mod.get("quantity", 1)):
                km_pool.append({"type_id": mod["type_id"], "used": False})

        for doc_mod in doctrine_mods:
            doc_type_id = doc_mod.get("type_id", 0)
            doc_qty = doc_mod.get("quantity", 1)
            doc_name = doc_mod.get("type_name", f"Type {doc_type_id}")

            for _ in range(doc_qty):
                matched = False

                # Try exact match first
                for km_item in km_pool:
                    if not km_item["used"] and km_item["type_id"] == doc_type_id:
                        km_item["used"] = True
                        result["exact"].append({
                            "slot": slot,
                            "doctrine_type_id": doc_type_id,
                            "killmail_type_id": doc_type_id,
                            "type_name": doc_name,
                            "status": "exact",
                        })
                        matched = True
                        break

                if matched:
                    continue

                # Try fuzzy match (same group, different meta)
                doc_group_id = self._get_group_id(doc_type_id)
                doc_meta = self._get_meta_level(doc_type_id)

                for km_item in km_pool:
                    if km_item["used"]:
                        continue

                    km_type_id = km_item["type_id"]

                    # Check for abyssal module
                    if km_type_id >= ABYSSAL_MIN_TYPE_ID:
                        km_item["used"] = True
                        result["review_required"].append({
                            "slot": slot,
                            "doctrine_type_id": doc_type_id,
                            "killmail_type_id": km_type_id,
                            "type_name": doc_name,
                            "status": "review_required",
                            "reason": "Abyssal/mutated module",
                        })
                        matched = True
                        break

                    km_group_id = self._get_group_id(km_type_id)
                    if km_group_id and km_group_id == doc_group_id:
                        km_meta = self._get_meta_level(km_type_id)
                        km_name = self._get_type_name(km_type_id)
                        km_item["used"] = True

                        if km_meta < doc_meta:
                            result["downgrades"].append({
                                "slot": slot,
                                "doctrine_type_id": doc_type_id,
                                "killmail_type_id": km_type_id,
                                "doctrine_name": doc_name,
                                "killmail_name": km_name,
                                "status": "downgrade",
                                "meta_diff": doc_meta - km_meta,
                            })
                        else:
                            result["upgrades"].append({
                                "slot": slot,
                                "doctrine_type_id": doc_type_id,
                                "killmail_type_id": km_type_id,
                                "doctrine_name": doc_name,
                                "killmail_name": km_name,
                                "status": "upgrade",
                                "meta_diff": km_meta - doc_meta,
                            })
                        matched = True
                        break

                if not matched:
                    result["missing"].append({
                        "slot": slot,
                        "doctrine_type_id": doc_type_id,
                        "type_name": doc_name,
                        "status": "missing",
                    })

        # Extra items not in doctrine
        for km_item in km_pool:
            if not km_item["used"]:
                name = self._get_type_name(km_item["type_id"])
                result["extra"].append({
                    "slot": slot,
                    "killmail_type_id": km_item["type_id"],
                    "type_name": name,
                    "status": "extra",
                })

        return dict(result)

    def _match_drones(
        self, doctrine_drones: list, killmail_drones: list
    ) -> dict:
        """Match drone bay contents."""
        result = defaultdict(list)

        doc_counts: dict[int, int] = {}
        for d in doctrine_drones:
            tid = d.get("type_id", 0)
            doc_counts[tid] = doc_counts.get(tid, 0) + d.get("quantity", 1)

        km_counts: dict[int, int] = {}
        for d in killmail_drones:
            tid = d.get("type_id", 0)
            km_counts[tid] = km_counts.get(tid, 0) + d.get("quantity", 1)

        for doc_tid, doc_qty in doc_counts.items():
            km_qty = km_counts.pop(doc_tid, 0)
            name = self._get_type_name(doc_tid) or f"Type {doc_tid}"

            matched_qty = min(doc_qty, km_qty)
            if matched_qty > 0:
                result["exact"].append({
                    "slot": "drones",
                    "doctrine_type_id": doc_tid,
                    "killmail_type_id": doc_tid,
                    "type_name": name,
                    "status": "exact",
                    "quantity": matched_qty,
                })

            missing_qty = doc_qty - km_qty
            if missing_qty > 0:
                result["missing"].append({
                    "slot": "drones",
                    "doctrine_type_id": doc_tid,
                    "type_name": name,
                    "status": "missing",
                    "quantity": missing_qty,
                })

        # Extra drones not in doctrine
        for km_tid, km_qty in km_counts.items():
            name = self._get_type_name(km_tid) or f"Type {km_tid}"
            result["extra"].append({
                "slot": "drones",
                "killmail_type_id": km_tid,
                "type_name": name,
                "status": "extra",
                "quantity": km_qty,
            })

        return dict(result)

    def _calculate_match_score(self, match_result: dict) -> float:
        """Calculate a 0.00-1.00 match score.

        Weights:
        - exact: 1.0
        - upgrade: 1.0 (valid, just capped payout)
        - downgrade: 0.7
        - review_required: 0.5
        - missing: 0.0
        - extra: ignored (doesn't count against)
        """
        weights = {
            "exact": 1.0,
            "upgrades": 1.0,
            "downgrades": 0.7,
            "review_required": 0.5,
            "missing": 0.0,
        }

        total_items = 0
        weighted_sum = 0.0

        for category, weight in weights.items():
            items = match_result.get(category, [])
            count = sum(item.get("quantity", 1) for item in items)
            total_items += count
            weighted_sum += count * weight

        if total_items == 0:
            return 0.0

        return round(weighted_sum / total_items, 2)

    def find_best_doctrine(
        self, corporation_id: int, ship_type_id: int, killmail_items: dict
    ) -> Optional[dict]:
        """Find the best matching active doctrine for a ship type.

        Returns the doctrine with the highest match score, or None
        if no doctrines exist for this ship type.
        """
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, fitting_json, base_payout
                FROM fleet_doctrines
                WHERE corporation_id = %s
                  AND ship_type_id = %s
                  AND is_active = TRUE
                """,
                (corporation_id, ship_type_id),
            )
            doctrines = cur.fetchall()

        if not doctrines:
            return None

        best_match = None
        best_score = -1.0

        for doc in doctrines:
            fitting = doc["fitting_json"]
            if isinstance(fitting, str):
                import json
                fitting = json.loads(fitting)

            match_result = self.match_fitting(killmail_items, fitting)
            score = match_result["match_score"]

            if score > best_score:
                best_score = score
                best_match = {
                    "doctrine_id": doc["id"],
                    "doctrine_name": doc["name"],
                    "base_payout": doc["base_payout"],
                    "match_result": match_result,
                    "match_score": score,
                }

        return best_match

    # ──────────────────────────── SDE HELPERS ──────────────────────────────

    def _get_group_id(self, type_id: int) -> Optional[int]:
        """Get the group_id for a type from SDE."""
        with self.db.cursor() as cur:
            cur.execute(
                'SELECT "groupID" FROM "invTypes" WHERE "typeID" = %s',
                (type_id,),
            )
            row = cur.fetchone()
        return row["groupID"] if row else None

    def _get_meta_level(self, type_id: int) -> int:
        """Get the meta-level for a type from SDE dgmTypeAttributes.

        Attribute 633 = metaLevel. Returns 0 if not found.
        """
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT "valueFloat", "valueInt"
                FROM "dgmTypeAttributes"
                WHERE "typeID" = %s AND "attributeID" = %s
                """,
                (type_id, ATTR_META_LEVEL),
            )
            row = cur.fetchone()
        if not row:
            return 0
        return int(row["valueFloat"] or row["valueInt"] or 0)

    def _get_type_name(self, type_id: int) -> Optional[str]:
        """Get type name from SDE."""
        with self.db.cursor() as cur:
            cur.execute(
                'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                (type_id,),
            )
            row = cur.fetchone()
        return row["typeName"] if row else None
