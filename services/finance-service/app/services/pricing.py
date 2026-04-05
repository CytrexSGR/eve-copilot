"""Pricing Engine for SRP valuations.

Syncs item prices from Fuzzwork API and calculates fitting values
using the configured pricing mode (jita_buy, jita_sell, jita_split).
"""

import logging
from decimal import Decimal
from typing import Optional

import httpx
from eve_shared import get_db

from app.config import settings

logger = logging.getLogger(__name__)

from eve_shared.constants import JITA_STATION_ID

FUZZWORK_BATCH_SIZE = 200  # Max type IDs per Fuzzwork API call


class PricingEngine:
    """Manages item price sync and fitting valuation."""

    def __init__(self):
        self.db = get_db()

    async def sync_item_prices(self, type_ids: list[int]) -> int:
        """Fetch current Jita prices from Fuzzwork and update item_prices table.

        Returns number of items updated.
        """
        if not type_ids:
            return 0

        unique_ids = list(set(type_ids))
        updated = 0

        for batch_start in range(0, len(unique_ids), FUZZWORK_BATCH_SIZE):
            batch = unique_ids[batch_start:batch_start + FUZZWORK_BATCH_SIZE]
            ids_param = ",".join(str(tid) for tid in batch)

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(
                        settings.fuzzwork_api_url,
                        params={
                            "types": ids_param,
                            "station": JITA_STATION_ID,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as e:
                logger.error("Fuzzwork API error for batch %d: %s", batch_start, e)
                continue

            for type_id_str, prices in data.items():
                try:
                    type_id = int(type_id_str)
                    buy = Decimal(str(prices.get("buy", {}).get("max", 0)))
                    sell = Decimal(str(prices.get("sell", {}).get("min", 0)))
                    split = (buy + sell) / 2

                    self._upsert_price(type_id, buy, sell, split)
                    updated += 1
                except (ValueError, KeyError) as e:
                    logger.debug("Skip price for %s: %s", type_id_str, e)

        logger.info("Synced %d item prices from Fuzzwork", updated)
        return updated

    def _upsert_price(
        self,
        type_id: int,
        jita_buy: Decimal,
        jita_sell: Decimal,
        jita_split: Decimal,
    ):
        """Insert or update a price in item_prices."""
        with self.db.cursor() as cur:
            # Resolve type name, group_id and meta_level from SDE
            cur.execute(
                """
                SELECT t."typeName", t."groupID"
                FROM "invTypes" t
                WHERE t."typeID" = %s
                """,
                (type_id,),
            )
            sde_row = cur.fetchone()
            type_name = sde_row["typeName"] if sde_row else None
            group_id = sde_row["groupID"] if sde_row else None

            cur.execute(
                """
                SELECT COALESCE("valueFloat", "valueInt", 0)::int as meta
                FROM "dgmTypeAttributes"
                WHERE "typeID" = %s AND "attributeID" = 633
                """,
                (type_id,),
            )
            meta_row = cur.fetchone()
            meta_level = meta_row["meta"] if meta_row else 0

            cur.execute(
                """
                INSERT INTO item_prices
                    (type_id, type_name, group_id, meta_level,
                     jita_buy, jita_sell, jita_split, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (type_id) DO UPDATE
                SET type_name = EXCLUDED.type_name,
                    group_id = EXCLUDED.group_id,
                    meta_level = EXCLUDED.meta_level,
                    jita_buy = EXCLUDED.jita_buy,
                    jita_sell = EXCLUDED.jita_sell,
                    jita_split = EXCLUDED.jita_split,
                    updated_at = NOW()
                """,
                (type_id, type_name, group_id, meta_level,
                 jita_buy, jita_sell, jita_split),
            )

    def calculate_fitting_value(
        self, fitting: dict, pricing_mode: str = "jita_split"
    ) -> Decimal:
        """Calculate total value of a fitting using stored prices.

        pricing_mode: 'jita_buy', 'jita_sell', or 'jita_split'
        """
        total = Decimal("0.00")
        price_col = pricing_mode  # Column name matches mode

        for slot in ("high", "med", "low", "rig", "drones"):
            for mod in fitting.get(slot, []):
                type_id = mod.get("type_id", 0)
                qty = mod.get("quantity", 1)

                with self.db.cursor() as cur:
                    cur.execute(
                        f'SELECT {price_col} FROM item_prices WHERE type_id = %s',
                        (type_id,),
                    )
                    row = cur.fetchone()

                if row and row[price_col]:
                    total += Decimal(str(row[price_col])) * qty

        return total

    def calculate_killmail_value(
        self, killmail_items: dict, pricing_mode: str = "jita_split"
    ) -> Decimal:
        """Calculate total value of killmail fitted items."""
        total = Decimal("0.00")
        price_col = pricing_mode

        for slot in ("high", "med", "low", "rig", "drones"):
            for mod in killmail_items.get(slot, []):
                type_id = mod.get("type_id", 0)
                qty = mod.get("quantity", 1)

                with self.db.cursor() as cur:
                    cur.execute(
                        f'SELECT {price_col} FROM item_prices WHERE type_id = %s',
                        (type_id,),
                    )
                    row = cur.fetchone()

                if row and row[price_col]:
                    total += Decimal(str(row[price_col])) * qty

        return total

    def get_insurance_payout(
        self, ship_type_id: int, level: str = "none"
    ) -> Decimal:
        """Estimate insurance payout for a ship.

        Insurance payouts are roughly based on base hull price.
        Level multipliers (approximate):
        - none: 0% (40% of base material value)
        - basic: 50%
        - standard: 60%
        - bronze: 70%
        - silver: 80%
        - gold: 90%
        - platinum: 100%
        """
        if level == "none":
            return Decimal("0.00")

        # Get ship base price from SDE (basePrice attribute)
        with self.db.cursor() as cur:
            cur.execute(
                'SELECT "basePrice" FROM "invTypes" WHERE "typeID" = %s',
                (ship_type_id,),
            )
            row = cur.fetchone()

        if not row or not row["basePrice"]:
            return Decimal("0.00")

        base_price = Decimal(str(row["basePrice"]))

        # Insurance multipliers (percentage of base material value)
        multipliers = {
            "basic": Decimal("0.50"),
            "standard": Decimal("0.60"),
            "bronze": Decimal("0.70"),
            "silver": Decimal("0.80"),
            "gold": Decimal("0.90"),
            "platinum": Decimal("1.00"),
        }

        mult = multipliers.get(level, Decimal("0.00"))
        return (base_price * mult).quantize(Decimal("0.01"))

    def collect_fitting_type_ids(self, fitting: dict) -> list[int]:
        """Collect all type_ids from a fitting structure for price sync."""
        type_ids = set()
        for slot in ("high", "med", "low", "rig", "drones"):
            for mod in fitting.get(slot, []):
                tid = mod.get("type_id")
                if tid:
                    type_ids.add(tid)
        return list(type_ids)
