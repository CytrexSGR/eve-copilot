"""Mining Observer sync and tax calculation.

Implements:
- Observer discovery and ledger sync from ESI
- Composite key deduplification (observer_id + character_id + type_id + date)
- Delta calculation for taxable amounts
- Reprocessed value calculation via SDE invTypeMaterials × market prices
- Configurable tax rates and reprocessing yield per corporation
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional

import httpx
from eve_shared import get_db
from eve_shared.esi import EsiClient, esi_circuit_breaker

from app.config import settings

logger = logging.getLogger(__name__)


class MiningTaxService:
    """Mining observer sync, delta tracking, and tax calculation."""

    def __init__(self):
        self.esi = EsiClient()
        self.db = get_db()

    async def _get_corp_token(self, character_id: int) -> Optional[str]:
        """Get valid ESI token via auth-service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.auth_service_url}/api/auth/token/{character_id}"
                )
                resp.raise_for_status()
                return resp.json()["access_token"]
        except Exception as e:
            logger.error("Failed to get token for character %s: %s", character_id, e)
            return None

    def _get_tax_config(self, corp_id: int) -> dict:
        """Get mining tax config for corporation, or defaults."""
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT tax_rate, reprocessing_yield, pricing_mode "
                "FROM mining_tax_config WHERE corporation_id = %s",
                (corp_id,),
            )
            row = cur.fetchone()
        if row:
            return {
                "tax_rate": float(row["tax_rate"]),
                "reprocessing_yield": float(row["reprocessing_yield"]),
                "pricing_mode": row["pricing_mode"],
            }
        return {
            "tax_rate": settings.default_tax_rate,
            "reprocessing_yield": settings.default_reprocessing_yield,
            "pricing_mode": "jita_split",
        }

    # --- Observer Sync ---

    async def sync_observers(self, corp_id: int, character_id: int) -> dict:
        """Discover and sync mining observers for a corporation."""
        result = {"observers_found": 0, "observers_updated": 0}

        if esi_circuit_breaker.is_open():
            result["error"] = "circuit_breaker_open"
            return result

        token = await self._get_corp_token(character_id)
        if not token:
            result["error"] = "token_unavailable"
            return result

        observers = self.esi.get(
            f"/corporations/{corp_id}/mining/observers/", token=token
        )
        if not observers or not isinstance(observers, list):
            return result

        result["observers_found"] = len(observers)

        with self.db.cursor() as cur:
            for obs in observers:
                cur.execute(
                    """INSERT INTO mining_observers
                       (observer_id, corporation_id, observer_type, last_updated)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (observer_id) DO UPDATE SET
                           last_updated = EXCLUDED.last_updated""",
                    (
                        obs["observer_id"],
                        corp_id,
                        obs.get("observer_type", "structure"),
                        obs.get("last_updated"),
                    ),
                )
                result["observers_updated"] += cur.rowcount

        return result

    async def sync_observer_ledger(
        self, corp_id: int, observer_id: int, character_id: int
    ) -> dict:
        """Sync mining ledger for a single observer.

        Uses composite key deduplification and delta calculation.
        """
        result = {
            "observer_id": observer_id,
            "entries_synced": 0,
            "deltas_computed": 0,
        }

        if esi_circuit_breaker.is_open():
            result["error"] = "circuit_breaker_open"
            return result

        token = await self._get_corp_token(character_id)
        if not token:
            result["error"] = "token_unavailable"
            return result

        # Fetch ledger (paginated via X-Pages)
        page = 1
        all_entries = []
        while page <= 20:  # Safety limit
            entries = self.esi.get(
                f"/corporations/{corp_id}/mining/observers/{observer_id}/",
                token=token,
                params={"page": page},
            )
            if not entries or not isinstance(entries, list):
                break
            all_entries.extend(entries)
            if len(entries) < 1000:  # Last page (ESI returns up to 1000 per page)
                break
            page += 1

        if not all_entries:
            return result

        config = self._get_tax_config(corp_id)

        with self.db.cursor() as cur:
            for entry in all_entries:
                char_id = entry["character_id"]
                type_id = entry["type_id"]
                quantity = entry["quantity"]
                last_updated = entry["last_updated"]  # YYYY-MM-DD string

                # Step 1: Get stored quantity for this composite key
                cur.execute(
                    """SELECT quantity FROM mining_observer_ledger
                       WHERE observer_id = %s AND character_id = %s
                       AND type_id = %s AND last_updated = %s""",
                    (observer_id, char_id, type_id, last_updated),
                )
                existing = cur.fetchone()

                stored_qty = existing["quantity"] if existing else 0

                # Step 2: Delta calculation per spec Section 4.1
                if quantity < stored_qty:
                    # Reset case: CCP cleared logs or new day
                    delta = quantity
                else:
                    delta = quantity - stored_qty

                # Step 3: UPSERT raw ledger
                cur.execute(
                    """INSERT INTO mining_observer_ledger
                       (observer_id, character_id, type_id, last_updated,
                        quantity, updated_at)
                       VALUES (%s, %s, %s, %s, %s, NOW())
                       ON CONFLICT (observer_id, character_id, type_id, last_updated)
                       DO UPDATE SET
                           quantity = EXCLUDED.quantity,
                           updated_at = NOW()""",
                    (observer_id, char_id, type_id, last_updated, quantity),
                )
                result["entries_synced"] += 1

                # Step 4: Compute tax if delta > 0
                if delta > 0:
                    isk_value = self._calculate_ore_value(
                        type_id, delta, config["reprocessing_yield"], config["pricing_mode"]
                    )
                    tax_amount = isk_value * Decimal(str(config["tax_rate"]))

                    cur.execute(
                        """INSERT INTO mining_tax_ledger
                           (observer_id, character_id, type_id, date,
                            quantity, delta_quantity, isk_value, tax_amount, tax_rate)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (observer_id, character_id, type_id, date)
                           DO UPDATE SET
                               quantity = mining_tax_ledger.quantity + EXCLUDED.delta_quantity,
                               delta_quantity = mining_tax_ledger.delta_quantity + EXCLUDED.delta_quantity,
                               isk_value = mining_tax_ledger.isk_value + EXCLUDED.isk_value,
                               tax_amount = mining_tax_ledger.tax_amount + EXCLUDED.tax_amount""",
                        (
                            observer_id,
                            char_id,
                            type_id,
                            last_updated,
                            quantity,
                            delta,
                            isk_value,
                            tax_amount,
                            config["tax_rate"],
                        ),
                    )
                    result["deltas_computed"] += 1

        logger.info(
            "Observer %s ledger sync: %s entries, %s deltas",
            observer_id,
            result["entries_synced"],
            result["deltas_computed"],
        )
        return result

    async def sync_all_observers(self, corp_id: int, character_id: int) -> dict:
        """Sync all observers and their ledgers for a corporation."""
        # First discover observers
        obs_result = await self.sync_observers(corp_id, character_id)
        if obs_result.get("error"):
            return obs_result

        # Get all observer IDs for this corp
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT observer_id FROM mining_observers WHERE corporation_id = %s",
                (corp_id,),
            )
            observers = [row["observer_id"] for row in cur.fetchall()]

        total_entries = 0
        total_deltas = 0
        for obs_id in observers:
            if esi_circuit_breaker.is_open():
                break
            res = await self.sync_observer_ledger(corp_id, obs_id, character_id)
            total_entries += res.get("entries_synced", 0)
            total_deltas += res.get("deltas_computed", 0)

        return {
            "observers": len(observers),
            "entries_synced": total_entries,
            "deltas_computed": total_deltas,
        }

    # --- Extraction Sync ---

    async def sync_extractions(self, corp_id: int, character_id: int) -> dict:
        """Sync moon extraction schedules from ESI."""
        result = {"extractions_synced": 0}

        if esi_circuit_breaker.is_open():
            result["error"] = "circuit_breaker_open"
            return result

        token = await self._get_corp_token(character_id)
        if not token:
            result["error"] = "token_unavailable"
            return result

        extractions = self.esi.get(
            f"/corporations/{corp_id}/mining/extractions/", token=token
        )
        if not extractions or not isinstance(extractions, list):
            return result

        with self.db.cursor() as cur:
            for ext in extractions:
                cur.execute(
                    """INSERT INTO mining_extractions
                       (structure_id, corporation_id, moon_id,
                        extraction_start_time, chunk_arrival_time, natural_decay_time, synced_at)
                       VALUES (%s, %s, %s, %s, %s, %s, NOW())
                       ON CONFLICT (structure_id, extraction_start_time) DO UPDATE SET
                           chunk_arrival_time = EXCLUDED.chunk_arrival_time,
                           natural_decay_time = EXCLUDED.natural_decay_time,
                           synced_at = NOW()""",
                    (
                        ext["structure_id"],
                        corp_id,
                        ext["moon_id"],
                        ext["extraction_start_time"],
                        ext["chunk_arrival_time"],
                        ext["natural_decay_time"],
                    ),
                )
                result["extractions_synced"] += 1

        logger.info(
            "Synced %s extractions for corp %s", result["extractions_synced"], corp_id
        )
        return result

    # --- Extraction Queries ---

    def get_extractions(self, corp_id: int) -> list[dict]:
        """Get recent and upcoming extractions for a corporation."""
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT structure_id, moon_id, extraction_start_time,
                          chunk_arrival_time, natural_decay_time
                   FROM mining_extractions
                   WHERE corporation_id = %s
                     AND natural_decay_time >= NOW() - INTERVAL '7 days'
                   ORDER BY chunk_arrival_time ASC""",
                (corp_id,),
            )
            rows = cur.fetchall()

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        results = []
        for row in rows:
            chunk_arrival = row["chunk_arrival_time"]
            natural_decay = row["natural_decay_time"]

            if now < chunk_arrival:
                status = "active"
            elif chunk_arrival <= now < natural_decay:
                status = "ready"
            else:
                status = "expired"

            results.append({
                "structure_id": row["structure_id"],
                "moon_id": row["moon_id"],
                "extraction_start_time": row["extraction_start_time"].isoformat(),
                "chunk_arrival_time": chunk_arrival.isoformat(),
                "natural_decay_time": natural_decay.isoformat(),
                "status": status,
            })

        return results

    # --- Performance Metrics ---

    def get_performance(self, corp_id: int, days: int = 30) -> dict:
        """Get mining performance metrics per structure and ore breakdown."""
        # Per-structure aggregation
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT mtl.observer_id,
                          SUM(mtl.isk_value) as total_isk,
                          COUNT(DISTINCT mtl.character_id) as unique_miners,
                          COUNT(DISTINCT mtl.date) as active_days
                   FROM mining_tax_ledger mtl
                   JOIN mining_observers mo ON mtl.observer_id = mo.observer_id
                   WHERE mo.corporation_id = %s
                     AND mtl.date >= CURRENT_DATE - INTERVAL '1 day' * %s
                   GROUP BY mtl.observer_id
                   ORDER BY total_isk DESC""",
                (corp_id, days),
            )
            structure_rows = cur.fetchall()

        # Ore breakdown by rarity
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT COALESCE(mot.rarity, 'unknown') as rarity,
                          SUM(mtl.isk_value) as total_isk
                   FROM mining_tax_ledger mtl
                   JOIN mining_observers mo ON mtl.observer_id = mo.observer_id
                   LEFT JOIN moon_ore_types mot ON mtl.type_id = mot.type_id
                   WHERE mo.corporation_id = %s
                     AND mtl.date >= CURRENT_DATE - INTERVAL '1 day' * %s
                   GROUP BY mot.rarity
                   ORDER BY total_isk DESC""",
                (corp_id, days),
            )
            ore_rows = cur.fetchall()

        # Calculate totals
        total_isk = sum(float(r["total_isk"] or 0) for r in structure_rows)
        isk_per_day = total_isk / days if days > 0 else 0.0

        structure_performance = []
        for r in structure_rows:
            struct_isk = float(r["total_isk"] or 0)
            structure_performance.append({
                "observer_id": r["observer_id"],
                "total_isk": struct_isk,
                "unique_miners": r["unique_miners"],
                "active_days": r["active_days"],
                "percentage": round(struct_isk / total_isk * 100, 1) if total_isk > 0 else 0.0,
            })

        ore_breakdown = []
        for r in ore_rows:
            ore_isk = float(r["total_isk"] or 0)
            ore_breakdown.append({
                "rarity": r["rarity"],
                "total_isk": ore_isk,
                "percentage": round(ore_isk / total_isk * 100, 1) if total_isk > 0 else 0.0,
            })

        return {
            "corporation_id": corp_id,
            "period_days": days,
            "total_isk_mined": total_isk,
            "isk_per_day": round(isk_per_day, 2),
            "structure_performance": structure_performance,
            "ore_breakdown": ore_breakdown,
        }

    # --- Tax Calculation ---

    def _calculate_ore_value(
        self, type_id: int, quantity: int, reprocessing_yield: float, pricing_mode: str
    ) -> Decimal:
        """Calculate ISK value of ore via reprocessed mineral prices.

        Uses SDE invTypeMaterials for ore composition and ore_market_prices
        for mineral valuations.
        """
        # Get reprocessing materials from SDE
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT materialTypeID, quantity
                   FROM "invTypeMaterials"
                   WHERE "typeID" = %s""",
                (type_id,),
            )
            materials = cur.fetchall()

        if not materials:
            # Fallback: use direct ore price if no reprocessing data
            return self._get_direct_price(type_id, quantity, pricing_mode)

        # Calculate reprocessed value
        total_value = Decimal("0.00")
        with self.db.cursor() as cur:
            for mat in materials:
                mat_type_id = mat["materialtypeid"]
                mat_qty_per_batch = mat["quantity"]

                # Get mineral price
                cur.execute(
                    f"SELECT {pricing_mode} as price FROM ore_market_prices "
                    "WHERE type_id = %s",
                    (mat_type_id,),
                )
                price_row = cur.fetchone()
                if not price_row or not price_row["price"]:
                    continue

                mineral_price = Decimal(str(price_row["price"]))

                # Minerals per unit of ore * yield * quantity mined
                # invTypeMaterials.quantity is per portionSize batch
                effective_minerals = (
                    Decimal(str(mat_qty_per_batch))
                    * Decimal(str(reprocessing_yield))
                    * Decimal(str(quantity))
                    / Decimal("100")  # portionSize is typically 100 for ores
                )

                total_value += effective_minerals * mineral_price

        return total_value

    def _get_direct_price(
        self, type_id: int, quantity: int, pricing_mode: str
    ) -> Decimal:
        """Fallback: get direct market price for an ore type."""
        with self.db.cursor() as cur:
            cur.execute(
                f"SELECT {pricing_mode} as price FROM ore_market_prices "
                "WHERE type_id = %s",
                (type_id,),
            )
            row = cur.fetchone()

        if not row or not row["price"]:
            return Decimal("0.00")

        return Decimal(str(row["price"])) * Decimal(str(quantity))

    def get_tax_summary(self, corp_id: int, days: int = 30) -> list[dict]:
        """Get mining tax summary per character for a corporation."""
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT mtl.character_id,
                          SUM(mtl.quantity) as total_quantity,
                          SUM(mtl.delta_quantity) as total_delta,
                          SUM(mtl.isk_value) as total_isk_value,
                          SUM(mtl.tax_amount) as total_tax
                   FROM mining_tax_ledger mtl
                   JOIN mining_observers mo ON mtl.observer_id = mo.observer_id
                   WHERE mo.corporation_id = %s
                     AND mtl.date >= CURRENT_DATE - INTERVAL '1 day' * %s
                   GROUP BY mtl.character_id
                   ORDER BY total_tax DESC""",
                (corp_id, days),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_character_ore_breakdown(
        self, character_id: int, corp_id: int, days: int = 30
    ) -> list[dict]:
        """Get ore breakdown for a specific character."""
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT mtl.type_id,
                          it."typeName" as type_name,
                          SUM(mtl.delta_quantity) as total_quantity,
                          SUM(mtl.isk_value) as total_value,
                          SUM(mtl.tax_amount) as total_tax
                   FROM mining_tax_ledger mtl
                   JOIN mining_observers mo ON mtl.observer_id = mo.observer_id
                   LEFT JOIN "invTypes" it ON mtl.type_id = it."typeID"
                   WHERE mo.corporation_id = %s
                     AND mtl.character_id = %s
                     AND mtl.date >= CURRENT_DATE - INTERVAL '1 day' * %s
                   GROUP BY mtl.type_id, it."typeName"
                   ORDER BY total_value DESC""",
                (corp_id, character_id, days),
            )
            return [dict(row) for row in cur.fetchall()]

    # --- Market Price Sync ---

    async def sync_ore_prices(self) -> dict:
        """Sync ore/mineral prices from Fuzzwork API."""
        result = {"prices_updated": 0}

        # Get all type_ids we need prices for:
        # 1. Ores from mining ledger
        # 2. Minerals from invTypeMaterials
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT type_id FROM mining_observer_ledger
                   UNION
                   SELECT DISTINCT "materialTypeID" FROM "invTypeMaterials"
                   WHERE "typeID" IN (SELECT DISTINCT type_id FROM mining_observer_ledger)"""
            )
            type_ids = [row["type_id"] for row in cur.fetchall()]

        if not type_ids:
            return result

        # Fuzzwork accepts comma-separated type IDs
        # Process in batches of 200
        for i in range(0, len(type_ids), 200):
            batch = type_ids[i : i + 200]
            type_id_str = ",".join(str(t) for t in batch)

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        settings.fuzzwork_api_url,
                        params={"types": type_id_str, "station": 60003760},  # Jita 4-4
                    )
                    resp.raise_for_status()
                    prices = resp.json()
            except Exception as e:
                logger.error("Fuzzwork API error: %s", e)
                continue

            with self.db.cursor() as cur:
                for tid_str, data in prices.items():
                    buy = data.get("buy", {}).get("max", 0) or 0
                    sell = data.get("sell", {}).get("min", 0) or 0
                    split = (float(buy) + float(sell)) / 2 if buy and sell else 0

                    cur.execute(
                        """INSERT INTO ore_market_prices
                           (type_id, jita_buy, jita_sell, jita_split, updated_at)
                           VALUES (%s, %s, %s, %s, NOW())
                           ON CONFLICT (type_id) DO UPDATE SET
                               jita_buy = EXCLUDED.jita_buy,
                               jita_sell = EXCLUDED.jita_sell,
                               jita_split = EXCLUDED.jita_split,
                               updated_at = NOW()""",
                        (int(tid_str), buy, sell, split),
                    )
                    result["prices_updated"] += 1

        logger.info("Synced %s ore/mineral prices from Fuzzwork", result["prices_updated"])
        return result
