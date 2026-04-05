"""Doctrine Management Service.

CRUD operations for fleet doctrines with EFT and DNA import support.
Doctrines are stored as normalized JSONB fitting structures.
"""

import json
import logging
import re
from typing import Optional

from eve_shared import get_db

logger = logging.getLogger(__name__)

# EFT block order: low, mid, high, rig (block 0-3), block 4+ = drones
SLOT_BLOCK_ORDER = ["low", "med", "high", "rig"]

# DNA format: shipTypeID:moduleID;qty:moduleID;qty::
# Flag ranges for slot classification
FLAG_HIGH = range(27, 35)   # 27-34
FLAG_MID = range(19, 27)    # 19-26
FLAG_LOW = range(11, 19)    # 11-18
FLAG_RIG = range(92, 100)   # 92-99
FLAG_DRONE = (87,)


class DoctrineService:
    """Manages fleet doctrine CRUD and import operations."""

    def __init__(self):
        self.db = get_db()

    # ──────────────────────────────────── CRUD ─────────────────────────────

    def create_doctrine(
        self,
        corporation_id: int,
        name: str,
        ship_type_id: int,
        fitting: dict,
        base_payout: Optional[float] = None,
        created_by: Optional[int] = None,
        category: Optional[str] = "general",
        actor_name: Optional[str] = None,
    ) -> dict:
        """Create a new doctrine."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fleet_doctrines
                    (corporation_id, name, ship_type_id, fitting_json,
                     base_payout, created_by, category)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, corporation_id, name, ship_type_id,
                          fitting_json, is_active, base_payout,
                          created_by, created_at, updated_at, category
                """,
                (
                    corporation_id, name, ship_type_id,
                    json.dumps(fitting), base_payout, created_by, category,
                ),
            )
            row = cur.fetchone()
            if row:
                self._log_changelog(
                    cur, row["id"], corporation_id,
                    created_by or 0, actor_name or "System",
                    "created",
                    {"name": name, "ship_type_id": ship_type_id, "category": category},
                )
        return self._row_to_dict(row)

    def get_doctrine(self, doctrine_id: int) -> Optional[dict]:
        """Get a single doctrine by ID."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT d.id, d.corporation_id, d.name, d.ship_type_id,
                       d.fitting_json, d.is_active, d.base_payout,
                       d.created_by, d.created_at, d.updated_at,
                       d.category, t."typeName" as ship_name
                FROM fleet_doctrines d
                LEFT JOIN "invTypes" t ON t."typeID" = d.ship_type_id
                WHERE d.id = %s
                """,
                (doctrine_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def list_doctrines(
        self,
        corporation_id: int,
        active_only: bool = True,
    ) -> list[dict]:
        """List doctrines for a corporation."""
        where = "d.corporation_id = %s"
        params: list = [corporation_id]
        if active_only:
            where += " AND d.is_active = TRUE"

        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT d.id, d.corporation_id, d.name, d.ship_type_id,
                       d.fitting_json, d.is_active, d.base_payout,
                       d.created_by, d.created_at, d.updated_at,
                       d.category, t."typeName" as ship_name
                FROM fleet_doctrines d
                LEFT JOIN "invTypes" t ON t."typeID" = d.ship_type_id
                WHERE {where}
                ORDER BY d.name
                """,
                params,
            )
            rows = cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update_doctrine(
        self, doctrine_id: int, updates: dict,
        actor_id: Optional[int] = None, actor_name: Optional[str] = None,
    ) -> Optional[dict]:
        """Update a doctrine's mutable fields."""
        sets = []
        params = []
        for key in ("name", "is_active", "base_payout", "category"):
            if key in updates and updates[key] is not None:
                sets.append(f"{key} = %s")
                params.append(updates[key])

        if "fitting" in updates and updates["fitting"] is not None:
            sets.append("fitting_json = %s")
            params.append(json.dumps(updates["fitting"]))

        if not sets:
            return self.get_doctrine(doctrine_id)

        sets.append("updated_at = NOW()")
        params.append(doctrine_id)

        with self.db.cursor() as cur:
            cur.execute(
                f"""
                UPDATE fleet_doctrines
                SET {', '.join(sets)}
                WHERE id = %s
                RETURNING id, corporation_id, name, ship_type_id,
                          fitting_json, is_active, base_payout,
                          created_by, created_at, updated_at, category
                """,
                params,
            )
            row = cur.fetchone()
            if row:
                self._log_changelog(
                    cur, doctrine_id, row["corporation_id"],
                    actor_id or 0, actor_name or "System",
                    "updated", {k: v for k, v in updates.items() if v is not None},
                )
        if not row:
            return None
        return self._row_to_dict(row)

    def archive_doctrine(
        self, doctrine_id: int,
        actor_id: Optional[int] = None, actor_name: Optional[str] = None,
    ) -> bool:
        """Soft-delete a doctrine by setting is_active = FALSE."""
        with self.db.cursor() as cur:
            # Get corporation_id before archiving
            cur.execute(
                "SELECT corporation_id FROM fleet_doctrines WHERE id = %s",
                (doctrine_id,),
            )
            doc_row = cur.fetchone()
            corp_id = doc_row["corporation_id"] if doc_row else 0

            cur.execute(
                """
                UPDATE fleet_doctrines
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = %s AND is_active = TRUE
                """,
                (doctrine_id,),
            )
            archived = cur.rowcount > 0
            if archived:
                self._log_changelog(
                    cur, doctrine_id, corp_id,
                    actor_id or 0, actor_name or "System",
                    "archived", {},
                )
            return archived

    # ──────────────────────────────── EFT IMPORT ───────────────────────────

    def import_from_eft(
        self,
        corporation_id: int,
        eft_text: str,
        base_payout: Optional[float] = None,
        created_by: Optional[int] = None,
    ) -> Optional[dict]:
        """Parse EFT text and create a doctrine.

        EFT format:
            [Ship Name, Fitting Name]

            Low Slot Module
            Low Slot Module

            Mid Slot Module

            High Slot Module, Ammo Name

            Rig Module

            Drone Name x5
        """
        lines = eft_text.strip().split("\n")
        if not lines:
            return None

        # Parse header: [Ship Name, Fitting Name]
        header = lines[0].strip()
        match = re.match(r"^\[(.+?),\s*(.+?)\]$", header)
        if not match:
            logger.warning("Invalid EFT header: %s", header)
            return None

        ship_name = match.group(1).strip()
        fitting_name = match.group(2).strip()

        # Split remaining lines by empty lines into blocks
        blocks: list[list[dict]] = []
        current_block: list[dict] = []

        for line in lines[1:]:
            trimmed = line.strip()
            if trimmed == "":
                if current_block:
                    blocks.append(current_block)
                    current_block = []
                continue
            if trimmed.startswith("[Empty "):
                continue

            parsed = self._parse_eft_line(trimmed)
            if parsed:
                current_block.append(parsed)

        if current_block:
            blocks.append(current_block)

        # Resolve ship type_id from name
        ship_type_id = self._resolve_type_id(ship_name)
        if not ship_type_id:
            logger.warning("Unknown ship type: %s", ship_name)
            return None

        # Resolve module type_ids and build fitting structure
        fitting = {"high": [], "med": [], "low": [], "rig": [], "drones": []}
        for block_idx, block in enumerate(blocks):
            if block_idx < 4:
                slot_name = SLOT_BLOCK_ORDER[block_idx]
            else:
                slot_name = "drones"

            for mod in block:
                type_id = self._resolve_type_id(mod["name"])
                if not type_id:
                    logger.debug("Unresolved module: %s", mod["name"])
                    continue
                fitting[slot_name].append({
                    "type_id": type_id,
                    "type_name": mod["name"],
                    "quantity": mod["quantity"],
                })

        return self.create_doctrine(
            corporation_id=corporation_id,
            name=fitting_name,
            ship_type_id=ship_type_id,
            fitting=fitting,
            base_payout=base_payout,
            created_by=created_by,
        )

    def _parse_eft_line(self, line: str) -> Optional[dict]:
        """Parse a single EFT line into {name, quantity, ammo}."""
        if not line:
            return None

        # Split by comma for ammo notation: "Module Name, Ammo Name"
        comma_idx = line.find(",")
        module_part = line[:comma_idx].strip() if comma_idx >= 0 else line.strip()

        # Handle quantity suffix: "Hammerhead II x5"
        quantity = 1
        qty_match = re.match(r"^(.+?)\s+x(\d+)$", module_part, re.IGNORECASE)
        if qty_match:
            module_part = qty_match.group(1).strip()
            quantity = int(qty_match.group(2))

        if not module_part:
            return None

        return {"name": module_part, "quantity": quantity}

    # ──────────────────────────────── DNA IMPORT ───────────────────────────

    def import_from_dna(
        self,
        corporation_id: int,
        name: str,
        dna_string: str,
        base_payout: Optional[float] = None,
        created_by: Optional[int] = None,
    ) -> Optional[dict]:
        """Parse DNA string and create a doctrine.

        DNA format: shipTypeID:moduleID;qty:moduleID;qty::
        Example: 24690:2048;1:2048;1:2205;1:3170;2::
        """
        parts = dna_string.strip().rstrip(":").split(":")
        if len(parts) < 2:
            logger.warning("Invalid DNA string: %s", dna_string)
            return None

        try:
            ship_type_id = int(parts[0])
        except ValueError:
            logger.warning("Invalid ship type ID in DNA: %s", parts[0])
            return None

        # Parse module entries
        fitting = {"high": [], "med": [], "low": [], "rig": [], "drones": []}
        for part in parts[1:]:
            if not part:
                continue
            segments = part.split(";")
            if len(segments) < 1:
                continue
            try:
                type_id = int(segments[0])
                qty = int(segments[1]) if len(segments) > 1 else 1
            except ValueError:
                continue

            # Classify module by looking up SDE slot info
            slot = self._classify_module_slot(type_id)
            type_name = self._resolve_type_name(type_id)
            fitting[slot].append({
                "type_id": type_id,
                "type_name": type_name,
                "quantity": qty,
            })

        return self.create_doctrine(
            corporation_id=corporation_id,
            name=name,
            ship_type_id=ship_type_id,
            fitting=fitting,
            base_payout=base_payout,
            created_by=created_by,
        )


    # ──────────────────────────── FITTING IMPORT ───────────────────────────

    def import_from_fitting(
        self,
        corporation_id: int,
        name: str,
        ship_type_id: int,
        items: list,
        base_payout: float = 0,
        category: str = 'general',
        created_by: int = None,
    ) -> dict:
        """Convert a fitting's items to doctrine format and save.

        Maps ESI fitting flags to slot categories:
        - Flags 27-34: high slots
        - Flags 19-26: med slots
        - Flags 11-18: low slots
        - Flags 92-94: rig slots
        - Flags 87-91 or flag 5: drone bay
        - Flags 125-132: subsystems
        """
        high, med, low, rig, drones, subsystems = [], [], [], [], [], []

        for item in items:
            type_id = item.get('type_id') if isinstance(item, dict) else getattr(item, 'type_id', 0)
            flag = item.get('flag', 0) if isinstance(item, dict) else getattr(item, 'flag', 0)
            qty = item.get('quantity', 1) if isinstance(item, dict) else getattr(item, 'quantity', 1)
            type_name = self._resolve_type_name(type_id) or f'Type {type_id}'
            entry = {'type_id': type_id, 'type_name': type_name, 'quantity': qty}

            if 27 <= flag <= 34:
                high.append(entry)
            elif 19 <= flag <= 26:
                med.append(entry)
            elif 11 <= flag <= 18:
                low.append(entry)
            elif 92 <= flag <= 94:
                rig.append(entry)
            elif flag == 5 or 87 <= flag <= 91:
                drones.append(entry)
            elif 125 <= flag <= 132:
                subsystems.append(entry)
            else:
                # Unknown flag - classify via SDE
                slot = self._classify_module_slot(type_id)
                if slot == 'high':
                    high.append(entry)
                elif slot == 'med':
                    med.append(entry)
                elif slot == 'low':
                    low.append(entry)
                elif slot == 'rig':
                    rig.append(entry)
                elif slot == 'drones':
                    drones.append(entry)
                else:
                    low.append(entry)

        fitting_json = {'high': high, 'med': med, 'low': low, 'rig': rig, 'drones': drones}
        if subsystems:
            fitting_json['subsystems'] = subsystems

        return self.create_doctrine(
            corporation_id=corporation_id,
            name=name,
            ship_type_id=ship_type_id,
            fitting=fitting_json,
            base_payout=base_payout if base_payout else None,
            created_by=created_by,
            category=category,
        )

    # ──────────────────────────── SDE HELPERS ──────────────────────────────

    def _resolve_type_id(self, type_name: str) -> Optional[int]:
        """Resolve a type name to type_id using SDE invTypes."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT "typeID" FROM "invTypes"
                WHERE "typeName" = %s AND published = 1
                LIMIT 1
                """,
                (type_name,),
            )
            row = cur.fetchone()
        if row:
            return row["typeID"]

        # Try case-insensitive fallback
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT "typeID" FROM "invTypes"
                WHERE LOWER("typeName") = LOWER(%s) AND published = 1
                LIMIT 1
                """,
                (type_name,),
            )
            row = cur.fetchone()
        return row["typeID"] if row else None

    def _resolve_type_name(self, type_id: int) -> Optional[str]:
        """Resolve a type_id to its name."""
        with self.db.cursor() as cur:
            cur.execute(
                'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                (type_id,),
            )
            row = cur.fetchone()
        return row["typeName"] if row else None

    def _classify_module_slot(self, type_id: int) -> str:
        """Classify a module into a slot type using SDE dgmTypeEffects.

        Effect IDs: loPower=11, medPower=13, hiPower=12, rigSlot=2663
        """
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT "effectID" FROM "dgmTypeEffects"
                WHERE "typeID" = %s
                  AND "effectID" IN (11, 12, 13, 2663)
                """,
                (type_id,),
            )
            rows = cur.fetchall()

        effect_ids = {r["effectID"] for r in rows}
        if 12 in effect_ids:
            return "high"
        if 13 in effect_ids:
            return "med"
        if 11 in effect_ids:
            return "low"
        if 2663 in effect_ids:
            return "rig"

        # Check if it's a drone (categoryID = 18)
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT c."categoryID"
                FROM "invTypes" t
                JOIN "invGroups" g ON g."groupID" = t."groupID"
                JOIN "invCategories" c ON c."categoryID" = g."categoryID"
                WHERE t."typeID" = %s
                """,
                (type_id,),
            )
            row = cur.fetchone()
        if row and row["categoryID"] == 18:
            return "drones"

        return "low"  # Default fallback


    # ──────────────────────────── CLONE ─────────────────────────────────────

    def clone_doctrine(
        self,
        doctrine_id: int,
        new_name: str,
        category: Optional[str] = None,
        actor_id: int = 0,
        actor_name: str = "System",
    ) -> Optional[dict]:
        """Clone an existing doctrine with a new name and optional category."""
        original = self.get_doctrine(doctrine_id)
        if not original:
            return None

        clone_category = category or original.get("category", "general")
        fitting = original.get("fitting_json", {})
        if isinstance(fitting, str):
            fitting = json.loads(fitting)

        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fleet_doctrines
                    (corporation_id, name, ship_type_id, fitting_json,
                     base_payout, created_by, category)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, corporation_id, name, ship_type_id,
                          fitting_json, is_active, base_payout,
                          created_by, created_at, updated_at, category
                """,
                (
                    original["corporation_id"],
                    new_name,
                    original["ship_type_id"],
                    json.dumps(fitting),
                    original.get("base_payout"),
                    actor_id or original.get("created_by"),
                    clone_category,
                ),
            )
            row = cur.fetchone()
            if row:
                self._log_changelog(
                    cur, row["id"], original["corporation_id"],
                    actor_id, actor_name, "cloned",
                    {"cloned_from": doctrine_id, "original_name": original["name"]},
                )
        return self._row_to_dict(row) if row else None

    # ──────────────────────────── CHANGELOG ─────────────────────────────────

    def get_doctrine_changelog(
        self,
        doctrine_id: Optional[int] = None,
        corporation_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get changelog entries filtered by doctrine or corporation."""
        where_clauses = []
        params: list = []

        if doctrine_id is not None:
            where_clauses.append("doctrine_id = %s")
            params.append(doctrine_id)
        if corporation_id is not None:
            where_clauses.append("corporation_id = %s")
            params.append(corporation_id)

        where = " AND ".join(where_clauses) if where_clauses else "TRUE"
        params.extend([limit, offset])

        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, doctrine_id, corporation_id, actor_character_id,
                       actor_name, action, changes, created_at
                FROM doctrine_changelog
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ──────────────────────────── AUTO-PRICING ──────────────────────────────

    def calculate_doctrine_price(self, doctrine_id: int) -> Optional[dict]:
        """Calculate total fitting price from cached Jita sell prices."""
        doctrine = self.get_doctrine(doctrine_id)
        if not doctrine:
            return None

        fitting = doctrine.get("fitting_json", {})
        if isinstance(fitting, str):
            fitting = json.loads(fitting)

        total_price = 0.0
        item_prices = {}

        with self.db.cursor() as cur:
            for slot in ("high", "med", "low", "rig", "drones"):
                for mod in fitting.get(slot, []):
                    type_id = mod.get("type_id", 0)
                    qty = mod.get("quantity", 1)
                    type_name = mod.get("type_name", str(type_id))

                    cur.execute(
                        "SELECT jita_sell FROM item_prices WHERE type_id = %s",
                        (type_id,),
                    )
                    price_row = cur.fetchone()
                    unit_price = float(price_row["jita_sell"]) if price_row and price_row["jita_sell"] else 0.0
                    line_total = unit_price * qty
                    total_price += line_total

                    item_prices[str(type_id)] = {
                        "name": type_name,
                        "quantity": qty,
                        "unit_price": unit_price,
                        "total": line_total,
                    }

        from datetime import datetime, timezone
        return {
            "doctrine_id": doctrine_id,
            "total_price": round(total_price, 2),
            "item_prices": item_prices,
            "price_source": "fuzzwork_jita",
            "priced_at": datetime.now(timezone.utc).isoformat(),
        }

    # ──────────────────────────── CHANGELOG HELPER ──────────────────────────

    @staticmethod
    def _log_changelog(
        cur,
        doctrine_id: int,
        corporation_id: int,
        actor_id: int,
        actor_name: str,
        action: str,
        changes: Optional[dict] = None,
    ):
        """Insert a changelog entry. Called within an existing cursor/transaction."""
        cur.execute(
            """
            INSERT INTO doctrine_changelog
                (doctrine_id, corporation_id, actor_character_id,
                 actor_name, action, changes)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                doctrine_id, corporation_id, actor_id,
                actor_name, action, json.dumps(changes or {}),
            ),
        )

    # ──────────────────────────── ROW MAPPING ──────────────────────────────

    def _row_to_dict(self, row) -> dict:
        """Convert a database row to a doctrine dict."""
        if not row:
            return {}
        d = dict(row)
        # Ensure fitting_json is a dict, not string
        if isinstance(d.get("fitting_json"), str):
            d["fitting_json"] = json.loads(d["fitting_json"])
        return d
