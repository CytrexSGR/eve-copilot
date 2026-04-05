"""SRP Workflow Service.

Handles the full SRP lifecycle: submission, auto-validation,
approval/rejection, payout list generation, and batch marking.
"""

import json
import logging
import os
from decimal import Decimal
from typing import Optional

import httpx
from eve_shared import get_db

from app.services.killmail_matcher import KillmailMatcher
from app.services.pricing import PricingEngine

logger = logging.getLogger(__name__)

CHARACTER_SERVICE_URL = os.environ.get(
    "CHARACTER_SERVICE_URL", "http://character-service:8000"
)

# Reverse mapping: slot name → flag range for compliance payload
FLAG_RANGES = {
    "high": range(27, 35),
    "med": range(19, 27),
    "low": range(11, 19),
    "rig": range(92, 100),
}


def _build_compliance_payload(
    doctrine_id: int, killmail_items: dict
) -> dict:
    """Convert slot-grouped killmail items to compliance API payload.

    The compliance endpoint expects {doctrine_id, killmail_items: [{type_id, flag}]}.
    Each quantity-expanded item gets a sequential flag from the slot's range.
    Drones all use flag 87.
    """
    flat_items = []

    for slot, flag_range in FLAG_RANGES.items():
        slot_items = killmail_items.get(slot, [])
        flag_iter = iter(flag_range)
        for item in slot_items:
            qty = item.get("quantity", 1)
            for _ in range(qty):
                try:
                    flag = next(flag_iter)
                except StopIteration:
                    break
                flat_items.append({
                    "type_id": item["type_id"],
                    "flag": flag,
                })

    # Drones: all use flag 87
    for item in killmail_items.get("drones", []):
        qty = item.get("quantity", 1)
        for _ in range(qty):
            flat_items.append({
                "type_id": item["type_id"],
                "flag": 87,
            })

    return {
        "doctrine_id": doctrine_id,
        "killmail_items": flat_items,
    }


async def _fetch_compliance_score(
    doctrine_id: int, killmail_items: dict
) -> Optional[float]:
    """Fetch Dogma compliance score from character-service.

    Returns compliance_score (0.0-1.0) on success, None on failure.
    Gracefully falls back to None so SRP submission is never blocked.
    """
    payload = _build_compliance_payload(doctrine_id, killmail_items)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{CHARACTER_SERVICE_URL}/api/doctrines/compliance",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return float(data.get("compliance_score", 0))
    except Exception as exc:
        logger.warning(
            "Dogma compliance check failed for doctrine %s: %s",
            doctrine_id,
            exc,
        )
        return None


def _should_auto_approve(
    match_score: float,
    compliance_score: Optional[float],
    threshold: float,
    has_review_required: bool,
) -> bool:
    """Determine if an SRP request should be auto-approved.

    Uses the HIGHER of fuzzy match_score and Dogma compliance_score.
    Returns False if review_required is set or both scores are too low.
    """
    if has_review_required:
        return False

    if match_score == 0 and compliance_score is None:
        return False

    effective_score = max(match_score, compliance_score or 0)
    return effective_score >= threshold


class SRPWorkflow:
    """Manages the SRP request lifecycle."""

    def __init__(self):
        self.db = get_db()
        self.matcher = KillmailMatcher()
        self.pricing = PricingEngine()

    async def submit_request(
        self,
        corporation_id: int,
        character_id: int,
        character_name: Optional[str],
        killmail_id: int,
        killmail_hash: str,
        doctrine_id: Optional[int] = None,
    ) -> dict:
        """Submit a new SRP request.

        1. Fetch killmail from ESI
        2. Parse victim fitting
        3. Auto-match against active doctrines
        4. Calculate payout
        5. Dogma compliance enrichment
        6. Create srp_request record
        """
        # Check for duplicate
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT id FROM srp_requests WHERE killmail_id = %s",
                (killmail_id,),
            )
            existing = cur.fetchone()
        if existing:
            return {"error": "Duplicate submission", "existing_id": existing["id"]}

        # Fetch killmail
        km_data = await self.matcher.fetch_killmail(killmail_id, killmail_hash)
        if not km_data:
            return {"error": "Failed to fetch killmail from ESI"}

        victim = km_data.get("victim", {})
        ship_type_id = victim.get("ship_type_id")
        items = victim.get("items", [])

        # Get ship name from SDE
        ship_name = None
        with self.db.cursor() as cur:
            cur.execute(
                'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                (ship_type_id,),
            )
            row = cur.fetchone()
            if row:
                ship_name = row["typeName"]

        # Parse killmail items into slot structure
        killmail_items = self.matcher.parse_killmail_items(items)

        # Get SRP config
        config = self._get_srp_config(corporation_id)
        pricing_mode = config.get("pricing_mode", "jita_split")
        insurance_level = config.get("default_insurance_level", "none")
        auto_threshold = float(config.get("auto_approve_threshold", 0.90))
        max_payout = config.get("max_payout")

        # Sync prices for killmail items
        all_type_ids = []
        for slot_items in killmail_items.values():
            for item in slot_items:
                all_type_ids.append(item["type_id"])
        if all_type_ids:
            await self.pricing.sync_item_prices(all_type_ids)

        # Match against doctrines
        match_data = None
        matched_doctrine_id = doctrine_id

        if doctrine_id:
            # Use specified doctrine
            with self.db.cursor() as cur:
                cur.execute(
                    "SELECT fitting_json, base_payout FROM fleet_doctrines WHERE id = %s",
                    (doctrine_id,),
                )
                doc_row = cur.fetchone()
            if doc_row:
                fitting = doc_row["fitting_json"]
                if isinstance(fitting, str):
                    fitting = json.loads(fitting)
                match_data = self.matcher.match_fitting(killmail_items, fitting)

                # Sync doctrine item prices too
                doc_type_ids = self.pricing.collect_fitting_type_ids(fitting)
                if doc_type_ids:
                    await self.pricing.sync_item_prices(doc_type_ids)
        else:
            # Auto-find best matching doctrine
            best = self.matcher.find_best_doctrine(
                corporation_id, ship_type_id, killmail_items
            )
            if best:
                matched_doctrine_id = best["doctrine_id"]
                match_data = best["match_result"]

                # Sync doctrine prices
                with self.db.cursor() as cur:
                    cur.execute(
                        "SELECT fitting_json FROM fleet_doctrines WHERE id = %s",
                        (matched_doctrine_id,),
                    )
                    doc_row = cur.fetchone()
                if doc_row:
                    fitting = doc_row["fitting_json"]
                    if isinstance(fitting, str):
                        fitting = json.loads(fitting)
                    doc_type_ids = self.pricing.collect_fitting_type_ids(fitting)
                    if doc_type_ids:
                        await self.pricing.sync_item_prices(doc_type_ids)

        # Calculate values
        fitting_value = self.pricing.calculate_killmail_value(
            killmail_items, pricing_mode
        )
        insurance_payout = self.pricing.get_insurance_payout(
            ship_type_id, insurance_level
        )

        # Payout = fitting value - insurance (or doctrine base_payout if set)
        payout_amount = fitting_value - insurance_payout
        if payout_amount < 0:
            payout_amount = Decimal("0.00")

        # Apply max_payout cap
        if max_payout and payout_amount > Decimal(str(max_payout)):
            payout_amount = Decimal(str(max_payout))

        match_score = Decimal(str(
            match_data["match_score"] if match_data else 0
        ))
        match_result_json = json.dumps(match_data) if match_data else "{}"

        # Dogma compliance enrichment
        compliance_score = None
        if matched_doctrine_id:
            compliance_score = await _fetch_compliance_score(
                matched_doctrine_id, killmail_items
            )

        # Determine initial status using the higher of the two scores
        has_review = bool(match_data and match_data.get("review_required"))
        status = "approved" if _should_auto_approve(
            float(match_score), compliance_score, auto_threshold, has_review
        ) else "pending"
        scoring_method = (
            "dogma"
            if compliance_score is not None
            and compliance_score >= float(match_score)
            else "fuzzy"
        )

        # Insert SRP request
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO srp_requests
                    (corporation_id, character_id, character_name,
                     killmail_id, killmail_hash, ship_type_id, ship_name,
                     doctrine_id, payout_amount, fitting_value,
                     insurance_payout, status, match_result, match_score,
                     compliance_score, scoring_method)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    corporation_id, character_id, character_name,
                    killmail_id, killmail_hash, ship_type_id, ship_name,
                    matched_doctrine_id, payout_amount, fitting_value,
                    insurance_payout, status, match_result_json, match_score,
                    compliance_score, scoring_method,
                ),
            )
            row = cur.fetchone()

        result = dict(row)
        result["match_result"] = match_data or {}
        return result

    def get_payout_list(
        self, corporation_id: int, status: str = "approved"
    ) -> str:
        """Generate TSV payout list for EVE client mass payout.

        Format: CharacterName\tAmount\tReason
        """
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT character_name, payout_amount, killmail_id,
                       ship_name, id
                FROM srp_requests
                WHERE corporation_id = %s AND status = %s
                ORDER BY submitted_at
                """,
                (corporation_id, status),
            )
            rows = cur.fetchall()

        lines = []
        for row in rows:
            name = row["character_name"] or f"Character {row['id']}"
            amount = int(row["payout_amount"])  # EVE wants integers
            ship = row["ship_name"] or "Unknown"
            reason = f"SRP: {ship} Loss #{row['killmail_id']}"
            lines.append(f"{name}\t{amount}\t{reason}")

        return "\n".join(lines)

    def batch_mark_paid(
        self, request_ids: list[int]
    ) -> int:
        """Mark multiple SRP requests as paid.

        Returns number of rows updated.
        """
        if not request_ids:
            return 0

        with self.db.cursor() as cur:
            cur.execute(
                """
                UPDATE srp_requests
                SET status = 'paid', paid_at = NOW()
                WHERE id = ANY(%s) AND status = 'approved'
                """,
                (request_ids,),
            )
            return cur.rowcount

    def _get_srp_config(self, corporation_id: int) -> dict:
        """Get SRP config for a corporation, or defaults."""
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT * FROM srp_config WHERE corporation_id = %s",
                (corporation_id,),
            )
            row = cur.fetchone()

        if row:
            return dict(row)

        return {
            "pricing_mode": "jita_split",
            "default_insurance_level": "none",
            "auto_approve_threshold": 0.90,
            "max_payout": None,
        }
