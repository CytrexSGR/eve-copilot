"""Items derivation service for doctrine templates.

This service analyzes doctrine compositions and derives market items
(ammunition, fuel, modules) that are consumed in combat.

NEW APPROACH (v2): Extract items directly from killmail data instead of
manual ship-to-ammo mappings. This gives us REAL consumption data.
"""

import os
import re
import psycopg2
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from services.war_economy.doctrine.models import DoctrineTemplate, ItemOfInterest


# Item categories we care about (EVE Online group IDs)
ITEM_CATEGORIES = {
    # Ammunition
    "Hybrid Charge": "ammunition",
    "Projectile Ammo": "ammunition",
    "Frequency Crystal": "ammunition",
    "Cruise Missile": "ammunition",
    "Torpedo": "ammunition",
    "Heavy Missile": "ammunition",
    "Heavy Assault Missile": "ammunition",
    "Light Missile": "ammunition",
    "Rocket": "ammunition",
    "XL Torpedo": "ammunition",
    "XL Cruise Missile": "ammunition",
    "Bomb": "ammunition",
    "Advanced Blaster Charge": "ammunition",
    "Advanced Railgun Charge": "ammunition",
    "Advanced Beam Laser Crystal": "ammunition",
    "Advanced Pulse Laser Crystal": "ammunition",
    "Advanced Artillery Ammo": "ammunition",
    "Advanced Autocannon Ammo": "ammunition",
    "Advanced Cruise Missile": "ammunition",
    "Advanced Torpedo": "ammunition",

    # Fuel & Consumables
    "Ice Product": "fuel",
    "Fuel Block": "fuel",

    # Nanite Repair Paste
    "Nanite Repair Paste": "module",

    # Drones (often lost)
    "Combat Drone": "drone",
    "Logistics Drone": "drone",
    "Electronic Warfare Drone": "drone",
    "Fighter": "drone",
    "Fighter Bomber": "drone",

    # Charges
    "Cap Booster Charge": "module",
    "Scanner Probe": "module",
    "Survey Probe": "module",
}

# Priority mapping
CATEGORY_PRIORITY = {
    "ammunition": 1,
    "fuel": 1,
    "module": 2,
    "drone": 3,
}

# Ship type to ammunition mapping
# Maps ship type IDs to their primary ammunition types
SHIP_TO_AMMUNITION = {
    # Large Projectile Ships
    17738: [  # Machariel
        (21894, "Republic Fleet EMP L", 5000.0),   # Republic Fleet EMP L
        (12779, "Hail L", 5000.0),                  # Hail L
    ],
    24690: [  # Hurricane
        (21894, "Republic Fleet EMP L", 5000.0),
        (12779, "Hail L", 5000.0),
    ],
    # Medium Projectile Ships
    29990: [  # Loki
        (12777, "Hail M", 7500.0),                  # Hail M
        (12773, "Barrage M", 7500.0),              # Barrage M
    ],
    # Large Beam Laser Ships
    17736: [  # Nightmare
        (12824, "Aurora L", 5000.0),               # Aurora L
        (12818, "Scorch L", 5000.0),               # Scorch L
    ],
    # Heavy Assault Cruisers
    12015: [  # Muninn
        (21892, "Republic Fleet EMP M", 7500.0),   # Republic Fleet EMP M
        (12777, "Hail M", 7500.0),
    ],
    # HAM Ships
    12023: [  # Sacrilege
        (2679, "Caldari Navy Mjolnir Heavy Assault Missile", 10000.0),
    ],
    # Railgun Ships
    12011: [  # Eagle
        (230, "Antimatter Charge L", 5000.0),
        (20050, "Null L", 5000.0),
    ],
    37480: [  # Ferox (actually uses hybrid charges)
        (229, "Antimatter Charge M", 7500.0),
        (20049, "Null M", 7500.0),
    ],
    # HAM/Torpedo Ships
    11993: [  # Cerberus
        (24513, "Scourge Fury Heavy Assault Missile", 10000.0),
    ],
}

# Capital ship to fuel mapping (by faction)
# Type ID -> (fuel_type_id, fuel_name, consumption_rate)
CAPITAL_SHIP_FUEL = {
    # Amarr Capitals - use Heavy Water
    19720: (16272, "Heavy Water", 100.0),  # Revelation
    37604: (16272, "Heavy Water", 100.0),  # Apostle
    23913: (16272, "Heavy Water", 100.0),  # Archon
    3514: (16272, "Heavy Water", 100.0),   # Aeon
    671: (16272, "Heavy Water", 100.0),    # Avatar

    # Caldari Capitals - use Liquid Ozone
    19726: (16273, "Liquid Ozone", 100.0),  # Phoenix
    37605: (16273, "Liquid Ozone", 100.0),  # Minokawa
    23915: (16273, "Liquid Ozone", 100.0),  # Chimera
    22852: (16273, "Liquid Ozone", 100.0),  # Wyvern (actually Caldari supercap)
    23917: (16273, "Liquid Ozone", 100.0),  # Leviathan

    # Gallente Capitals - use Enriched Uranium
    19724: (44, "Enriched Uranium", 100.0),  # Moros
    37606: (44, "Enriched Uranium", 100.0),  # Ninazu
    23911: (44, "Enriched Uranium", 100.0),  # Thanatos
    3764: (44, "Enriched Uranium", 100.0),   # Nyx
    3778: (44, "Enriched Uranium", 100.0),   # Erebus

    # Minmatar Capitals - also use Liquid Ozone
    19722: (16273, "Liquid Ozone", 100.0),  # Naglfar
    37607: (16273, "Liquid Ozone", 100.0),  # Lif
    24483: (16273, "Liquid Ozone", 100.0),  # Nidhoggur
    23919: (16273, "Liquid Ozone", 100.0),  # Hel
    3513: (16273, "Liquid Ozone", 100.0),   # Ragnarok
}


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host="localhost",
        database="eve_sde",
        user="eve",
        password=os.environ.get("DB_PASSWORD", ""),
        options="-c client_min_messages=ERROR"
    )


class ItemsDeriver:
    """Derives market items from doctrine compositions using killmail data.

    Instead of manual mappings, we extract the actual items that were
    destroyed in battles associated with the doctrine.
    """

    def __init__(self):
        self.conn = None
        self.cur = None

    def _ensure_connection(self):
        """Ensure database connection is open."""
        if self.conn is None or self.conn.closed:
            self.conn = get_db_connection()
            self.cur = self.conn.cursor()

    def _close_connection(self):
        """Close database connection."""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        self.conn = None
        self.cur = None

    def _extract_battle_id(self, doctrine_name: str) -> Optional[int]:
        """Extract battle ID from doctrine name like 'Raven Fleet (Battle 3034)'."""
        match = re.search(r'\(Battle (\d+)\)', doctrine_name)
        if match:
            return int(match.group(1))
        return None

    def derive_items_for_doctrine(self, doctrine: DoctrineTemplate) -> List[ItemOfInterest]:
        """Derive market items from doctrine by analyzing battle killmails.

        Args:
            doctrine: The doctrine template to analyze

        Returns:
            List of ItemOfInterest objects derived from actual combat data
        """
        items: Dict[int, ItemOfInterest] = {}

        # Try to extract battle ID from doctrine name
        battle_id = self._extract_battle_id(doctrine.doctrine_name)

        if battle_id:
            # Get items from actual battle data
            battle_items = self._get_items_from_battle(battle_id, doctrine.id)
            for item in battle_items:
                items[item.type_id] = item
        else:
            # Fallback: just add critical modules
            self._add_critical_modules(doctrine, items)

        return list(items.values())

    def _get_items_from_battle(self, battle_id: int, doctrine_id: int) -> List[ItemOfInterest]:
        """Get consumed items from battle killmail data.

        Args:
            battle_id: The battle to analyze
            doctrine_id: The doctrine ID for the items

        Returns:
            List of ItemOfInterest from actual battle data
        """
        self._ensure_connection()

        items = []

        try:
            # Query destroyed items from the battle, grouped by category
            self.cur.execute("""
                SELECT
                    i.item_type_id,
                    t."typeName",
                    g."groupName",
                    SUM(i.quantity) as total_qty
                FROM killmail_items i
                JOIN killmails k ON i.killmail_id = k.killmail_id
                JOIN "invTypes" t ON i.item_type_id = t."typeID"
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE k.battle_id = %s
                  AND i.was_destroyed = true
                  AND i.quantity > 0
                GROUP BY i.item_type_id, t."typeName", g."groupName"
                ORDER BY total_qty DESC
                LIMIT 50
            """, (battle_id,))

            rows = self.cur.fetchall()

            for type_id, type_name, group_name, quantity in rows:
                # Determine category
                category = ITEM_CATEGORIES.get(group_name)

                if category:
                    priority = CATEGORY_PRIORITY.get(category, 3)

                    items.append(ItemOfInterest(
                        doctrine_id=doctrine_id,
                        type_id=type_id,
                        item_name=type_name,
                        item_category=category,
                        consumption_rate=float(quantity),  # Use actual quantity as rate
                        priority=priority,
                        created_at=datetime.now(),
                    ))

            # Always add critical modules if not present
            critical_type_ids = [item.type_id for item in items]

            # Nanite Repair Paste
            if 28668 not in critical_type_ids:
                items.append(ItemOfInterest(
                    doctrine_id=doctrine_id,
                    type_id=28668,
                    item_name="Nanite Repair Paste",
                    item_category="module",
                    consumption_rate=None,
                    priority=1,
                    created_at=datetime.now(),
                ))

            # Strontium Clathrates (for capitals)
            if 16275 not in critical_type_ids:
                items.append(ItemOfInterest(
                    doctrine_id=doctrine_id,
                    type_id=16275,
                    item_name="Strontium Clathrates",
                    item_category="fuel",
                    consumption_rate=None,
                    priority=1,
                    created_at=datetime.now(),
                ))

        except Exception as e:
            print(f"[ItemsDeriver] Error getting items from battle {battle_id}: {e}")

        return items

    def _add_critical_modules(
        self,
        doctrine: DoctrineTemplate,
        items: Dict[int, ItemOfInterest]
    ) -> None:
        """Add critical modules that are always needed (fallback)."""
        critical = [
            (28668, "Nanite Repair Paste", "module"),
            (16275, "Strontium Clathrates", "fuel"),
        ]

        for type_id, name, category in critical:
            if type_id not in items:
                items[type_id] = ItemOfInterest(
                    doctrine_id=doctrine.id,
                    type_id=type_id,
                    item_name=name,
                    item_category=category,
                    consumption_rate=None,
                    priority=1,
                    created_at=datetime.now(),
                )

        # Derive ammunition and fuel from ship composition
        self._derive_from_composition(doctrine, items)

    def _derive_from_composition(
        self,
        doctrine: DoctrineTemplate,
        items: Dict[int, ItemOfInterest]
    ) -> None:
        """Derive ammunition and fuel from doctrine ship composition.

        Args:
            doctrine: The doctrine template
            items: Dict to add items to (keyed by type_id)
        """
        if not doctrine.composition:
            return

        # Process each ship type in the composition
        for ship_type_id_str, percentage in doctrine.composition.items():
            ship_type_id = int(ship_type_id_str)

            # Check for ammunition mappings
            if ship_type_id in SHIP_TO_AMMUNITION:
                for ammo_type_id, ammo_name, consumption_rate in SHIP_TO_AMMUNITION[ship_type_id]:
                    if ammo_type_id not in items:
                        items[ammo_type_id] = ItemOfInterest(
                            doctrine_id=doctrine.id,
                            type_id=ammo_type_id,
                            item_name=ammo_name,
                            item_category="ammunition",
                            consumption_rate=consumption_rate,
                            priority=1,
                            created_at=datetime.now(),
                        )

            # Check for capital ship fuel mappings
            if ship_type_id in CAPITAL_SHIP_FUEL:
                fuel_type_id, fuel_name, consumption_rate = CAPITAL_SHIP_FUEL[ship_type_id]
                if fuel_type_id not in items:
                    items[fuel_type_id] = ItemOfInterest(
                        doctrine_id=doctrine.id,
                        type_id=fuel_type_id,
                        item_name=fuel_name,
                        item_category="fuel",
                        consumption_rate=consumption_rate,
                        priority=1,
                        created_at=datetime.now(),
                    )

    def save_items_for_doctrine(self, doctrine: DoctrineTemplate, items: List[ItemOfInterest]) -> int:
        """Save derived items to database.

        Args:
            doctrine: The doctrine template
            items: List of items to save

        Returns:
            Number of items saved
        """
        if not items:
            return 0

        self._ensure_connection()
        saved = 0

        try:
            for item in items:
                self.cur.execute("""
                    INSERT INTO doctrine_items_of_interest
                        (doctrine_id, type_id, item_name, item_category, consumption_rate, priority, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doctrine_id, type_id) DO UPDATE SET
                        item_name = EXCLUDED.item_name,
                        item_category = EXCLUDED.item_category,
                        consumption_rate = EXCLUDED.consumption_rate,
                        priority = EXCLUDED.priority
                """, (
                    doctrine.id,
                    item.type_id,
                    item.item_name,
                    item.item_category,
                    item.consumption_rate,
                    item.priority,
                    item.created_at
                ))
                saved += 1

            self.conn.commit()
        except Exception as e:
            print(f"[ItemsDeriver] Error saving items: {e}")
            self.conn.rollback()

        return saved

    def derive_and_save_for_all_doctrines(self) -> int:
        """Derive and save items for all doctrines that don't have items yet.

        Returns:
            Total number of items saved
        """
        self._ensure_connection()
        total_saved = 0

        try:
            # Get doctrines without items
            self.cur.execute("""
                SELECT dt.id, dt.doctrine_name, dt.region_id, dt.composition,
                       dt.confidence_score, dt.observation_count, dt.first_seen,
                       dt.last_seen, dt.total_pilots_avg, dt.created_at, dt.updated_at
                FROM doctrine_templates dt
                LEFT JOIN doctrine_items_of_interest di ON dt.id = di.doctrine_id
                WHERE di.id IS NULL
            """)

            rows = self.cur.fetchall()
            print(f"[ItemsDeriver] Found {len(rows)} doctrines without items")

            for row in rows:
                doctrine = DoctrineTemplate(
                    id=row[0],
                    doctrine_name=row[1],
                    region_id=row[2],
                    composition=row[3],
                    confidence_score=row[4],
                    observation_count=row[5],
                    first_seen=row[6],
                    last_seen=row[7],
                    total_pilots_avg=row[8],
                    created_at=row[9],
                    updated_at=row[10]
                )

                items = self.derive_items_for_doctrine(doctrine)
                saved = self.save_items_for_doctrine(doctrine, items)
                total_saved += saved

                if saved > 0:
                    print(f"[ItemsDeriver] Saved {saved} items for '{doctrine.doctrine_name}'")

        except Exception as e:
            print(f"[ItemsDeriver] Error processing doctrines: {e}")

        return total_saved
