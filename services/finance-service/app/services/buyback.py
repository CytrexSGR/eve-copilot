"""Buyback appraisal and request management."""
import os
import logging
import re
from decimal import Decimal
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Janice API endpoint
JANICE_API_URL = "https://janice.e-351.com/api/rest/v1/pricer"

# Ore/mineral category group IDs from SDE
ORE_GROUP_IDS = {18, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 465, 467, 468, 469}
MINERAL_GROUP_IDS = {18}  # Minerals market group
ORE_CATEGORY_ID = 25  # Asteroid category


class BuybackService:
    """Handles item appraisal via Janice and buyback calculations."""

    def __init__(self, db, janice_api_key: str = None):
        self.db = db
        self.janice_api_key = janice_api_key or os.environ.get("JANICE_API_KEY", "")

    def parse_eve_text(self, raw_text: str) -> list[dict]:
        """Parse EVE client copy-paste text into item list.

        Supports formats:
        - TSV: "Tritanium\t10000" (inventory copy)
        - Named: "Tritanium x 10000" or "Tritanium x10000"
        - Simple: "Tritanium 10000"
        - Single: "Tritanium" (quantity 1)
        """
        items = []
        for line in raw_text.strip().splitlines():
            line = line.strip()
            if not line:
                continue

            # TSV format (EVE inventory copy)
            if "\t" in line:
                parts = line.split("\t")
                name = parts[0].strip()
                qty = self._parse_quantity(parts[1]) if len(parts) > 1 else 1
            # "Item x Quantity" format
            elif re.search(r"\s+x\s*\d", line, re.IGNORECASE):
                match = re.match(r"(.+?)\s+x\s*(\d[\d,.]*)", line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    qty = self._parse_quantity(match.group(2))
                else:
                    name = line
                    qty = 1
            # "Item Quantity" (number at end)
            elif re.search(r"\s+\d[\d,.]*$", line):
                match = re.match(r"(.+?)\s+(\d[\d,.]+)$", line)
                if match:
                    name = match.group(1).strip()
                    qty = self._parse_quantity(match.group(2))
                else:
                    name = line
                    qty = 1
            else:
                name = line
                qty = 1

            if name:
                items.append({"name": name, "quantity": max(1, qty)})

        return items

    def _parse_quantity(self, text: str) -> int:
        """Parse quantity string, handling commas and dots."""
        text = text.strip().replace(",", "").replace(".", "")
        try:
            return int(text)
        except ValueError:
            return 1

    def appraise_items(self, items: list[dict]) -> list[dict]:
        """Call Janice API to get Jita prices for items.

        Args:
            items: List of {"name": str, "quantity": int}

        Returns:
            List of items with price data added.
        """
        if not items:
            return []

        # Build text payload for Janice (one item per line)
        lines = [f"{item['name']} x {item['quantity']}" for item in items]
        payload = "\n".join(lines)

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    JANICE_API_URL,
                    params={"key": self.janice_api_key},
                    headers={
                        "accept": "application/json",
                        "Content-Type": "text/plain",
                    },
                    content=payload,
                )
                resp.raise_for_status()
                janice_data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Janice API error: {e.response.status_code} {e.response.text}")
            raise ValueError(f"Janice API returned {e.response.status_code}")
        except Exception as e:
            logger.error(f"Janice API request failed: {e}")
            raise ValueError(f"Failed to reach Janice API: {e}")

        # Merge Janice results with our items
        results = []
        for i, item in enumerate(items):
            if i < len(janice_data):
                jd = janice_data[i]
                jita_sell = jd.get("sellPriceMin", 0) or 0
                jita_buy = jd.get("buyPriceMax", 0) or 0
                type_info = jd.get("itemType", {})
                volume = type_info.get("volume", 0) or 0

                results.append({
                    "name": type_info.get("name", item["name"]),
                    "type_id": type_info.get("eid"),
                    "quantity": item["quantity"],
                    "volume_per_unit": volume,
                    "total_volume": volume * item["quantity"],
                    "jita_sell_price": jita_sell,
                    "jita_buy_price": jita_buy,
                    "jita_sell_total": jita_sell * item["quantity"],
                    "jita_buy_total": jita_buy * item["quantity"],
                })
            else:
                results.append({
                    "name": item["name"],
                    "type_id": None,
                    "quantity": item["quantity"],
                    "volume_per_unit": 0,
                    "total_volume": 0,
                    "jita_sell_price": 0,
                    "jita_buy_price": 0,
                    "jita_sell_total": 0,
                    "jita_buy_total": 0,
                    "error": "Item not found on Janice",
                })

        return results

    def get_config(self, config_id: int) -> Optional[dict]:
        """Get a buyback configuration."""
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT * FROM buyback_configs WHERE id = %s", (config_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def list_configs(self, corporation_id: Optional[int] = None, active_only: bool = True) -> list[dict]:
        """List buyback configurations."""
        with self.db.cursor() as cur:
            conditions = []
            params = []
            if corporation_id:
                conditions.append("corporation_id = %s")
                params.append(corporation_id)
            if active_only:
                conditions.append("is_active = TRUE")

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cur.execute(f"SELECT * FROM buyback_configs {where} ORDER BY name", params)
            return [dict(row) for row in cur.fetchall()]

    def create_config(self, data: dict) -> dict:
        """Create a new buyback config."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO buyback_configs
                    (corporation_id, name, base_discount, ore_modifier, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (
                data["corporation_id"],
                data["name"],
                data.get("base_discount", 10.0),
                data.get("ore_modifier", 0.0),
                data.get("notes"),
            ))
            return dict(cur.fetchone())

    def calculate_buyback(
        self, appraised_items: list[dict], config_id: int
    ) -> dict:
        """Apply buyback discount to appraised items.

        Args:
            appraised_items: Items with Janice prices
            config_id: Buyback config to use

        Returns:
            Per-item buyback values + totals.
        """
        config = self.get_config(config_id)
        if not config:
            raise ValueError(f"Buyback config {config_id} not found")

        base_pct = Decimal("100") - Decimal(str(config["base_discount"]))
        ore_pct = base_pct - Decimal(str(config["ore_modifier"]))

        total_jita = Decimal("0")
        total_buyback = Decimal("0")
        result_items = []

        for item in appraised_items:
            jita_total = Decimal(str(item["jita_sell_total"]))
            total_jita += jita_total

            # Check if item is ore/mineral by name heuristic
            is_ore = self._is_ore_or_mineral(item.get("name", ""))
            pct = ore_pct if is_ore else base_pct
            buyback_value = jita_total * pct / Decimal("100")
            total_buyback += buyback_value

            result_items.append({
                **item,
                "is_ore": is_ore,
                "discount_pct": float(Decimal("100") - pct),
                "buyback_value": float(buyback_value),
            })

        return {
            "config": {
                "id": config["id"],
                "name": config["name"],
                "base_discount": float(config["base_discount"]),
                "ore_modifier": float(config["ore_modifier"]),
            },
            "items": result_items,
            "summary": {
                "total_jita_value": float(total_jita),
                "total_buyback_value": float(total_buyback),
                "effective_rate": float(
                    total_buyback / total_jita * Decimal("100")
                ) if total_jita > 0 else 0,
                "item_count": len(result_items),
                "total_volume": sum(i.get("total_volume", 0) for i in result_items),
            },
        }

    def _is_ore_or_mineral(self, name: str) -> bool:
        """Check if item name is ore or mineral (simple heuristic)."""
        minerals = {
            "tritanium", "pyerite", "mexallon", "isogen",
            "nocxium", "zydrine", "megacyte", "morphite",
        }
        ore_keywords = {
            "veldspar", "scordite", "pyroxeres", "plagioclase",
            "omber", "kernite", "jaspet", "hemorphite", "hedbergite",
            "gneiss", "dark ochre", "spodumain", "crokite", "bistot",
            "arkonor", "mercoxit", "ice", "compressed",
            "bezdnacine", "rakovene", "talassonite",
            "kylixium", "nocxite", "ueganite", "hezorime", "griemeer",
            "mordunium",
        }
        lower = name.lower()
        if lower in minerals:
            return True
        return any(kw in lower for kw in ore_keywords)

    def submit_request(
        self,
        character_id: int,
        character_name: Optional[str],
        corporation_id: int,
        config_id: int,
        raw_text: str,
    ) -> dict:
        """Full buyback workflow: parse → appraise → calculate → save."""
        items = self.parse_eve_text(raw_text)
        if not items:
            raise ValueError("No items parsed from text")

        appraised = self.appraise_items(items)
        result = self.calculate_buyback(appraised, config_id)

        # Save to DB
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO buyback_requests
                    (character_id, character_name, corporation_id, config_id,
                     items, raw_text, total_jita_value, total_buyback)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                RETURNING *
            """, (
                character_id,
                character_name,
                corporation_id,
                config_id,
                __import__("json").dumps(result["items"]),
                raw_text,
                result["summary"]["total_jita_value"],
                result["summary"]["total_buyback_value"],
            ))
            row = cur.fetchone()

        return {
            "request_id": row["id"],
            "status": row["status"],
            **result,
        }

    def list_requests(
        self,
        corporation_id: Optional[int] = None,
        character_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """List buyback requests with optional filters."""
        conditions = []
        params = []

        if corporation_id:
            conditions.append("corporation_id = %s")
            params.append(corporation_id)
        if character_id:
            conditions.append("character_id = %s")
            params.append(character_id)
        if status:
            conditions.append("status = %s")
            params.append(status)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        with self.db.cursor() as cur:
            cur.execute(f"""
                SELECT * FROM buyback_requests
                {where}
                ORDER BY created_at DESC
                LIMIT %s
            """, params)
            return [self._row_to_request(row) for row in cur.fetchall()]

    def _row_to_request(self, row: dict) -> dict:
        """Convert DB row to request dict."""
        return {
            "id": row["id"],
            "character_id": row["character_id"],
            "character_name": row["character_name"],
            "corporation_id": row["corporation_id"],
            "config_id": row["config_id"],
            "items": row["items"],
            "total_jita_value": float(row["total_jita_value"]),
            "total_buyback": float(row["total_buyback"]),
            "status": row["status"],
            "contract_id": row["contract_id"],
            "reviewer_note": row["reviewer_note"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
