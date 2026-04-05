"""
Fitting Service for EVE Co-Pilot
Provides fitting analysis including DPS calculations with all modifiers.
Migrated from monolith to character-service with eve_shared database pattern.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, field_validator
from psycopg2.extras import RealDictCursor

from app.services.auth_client import AuthClient


# ESI flag string → integer mapping
FLAG_STRING_MAP = {
    "LoSlot0": 11, "LoSlot1": 12, "LoSlot2": 13, "LoSlot3": 14,
    "LoSlot4": 15, "LoSlot5": 16, "LoSlot6": 17, "LoSlot7": 18,
    "MedSlot0": 19, "MedSlot1": 20, "MedSlot2": 21, "MedSlot3": 22,
    "MedSlot4": 23, "MedSlot5": 24, "MedSlot6": 25, "MedSlot7": 26,
    "HiSlot0": 27, "HiSlot1": 28, "HiSlot2": 29, "HiSlot3": 30,
    "HiSlot4": 31, "HiSlot5": 32, "HiSlot6": 33, "HiSlot7": 34,
    "RigSlot0": 92, "RigSlot1": 93, "RigSlot2": 94,
    "SubSystemSlot0": 125, "SubSystemSlot1": 126,
    "SubSystemSlot2": 127, "SubSystemSlot3": 128,
    "DroneBay": 87, "FighterBay": 158, "Cargo": 5,
    "ServiceSlot0": 164, "ServiceSlot1": 165, "ServiceSlot2": 166,
}


def parse_flag(value: Union[int, str]) -> int:
    """Convert ESI flag (int or string like 'LoSlot1') to integer."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if value in FLAG_STRING_MAP:
            return FLAG_STRING_MAP[value]
        # Try direct int parse
        try:
            return int(value)
        except ValueError:
            return 0  # Unknown flag
    return 0


class FittingItem(BaseModel):
    """Item in a fitting."""
    type_id: int
    flag: int
    quantity: int

    @field_validator("flag", mode="before")
    @classmethod
    def coerce_flag(cls, v: Any) -> int:
        return parse_flag(v)


class ESIFitting(BaseModel):
    """ESI fitting format."""
    fitting_id: Optional[int] = None
    name: str
    description: str = ""
    ship_type_id: int
    items: List[FittingItem]


class DamageBreakdown(BaseModel):
    """DPS by damage type."""
    em: float
    thermal: float
    kinetic: float
    explosive: float
    total: float


class FittingAnalysis(BaseModel):
    """Analysis result for a fitting."""
    fitting_name: str
    ship_type_id: int
    ship_name: str
    weapon_count: int
    base_dps: float
    skill_multiplier: float
    ship_bonus_multiplier: float
    module_bonus_multiplier: float
    total_dps: float
    damage_breakdown: DamageBreakdown
    ammo_name: str
    active_modules: List[str]


class FittingService:
    """Service for fitting analysis."""

    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis
        self.auth_client = AuthClient()

    def _get_token(self, character_id: int) -> Optional[str]:
        """Get access token for character from auth-service."""
        return self.auth_client.get_valid_token(character_id)

    def get_character_fittings(self, character_id: int) -> List[ESIFitting]:
        """Get all fittings for a character from ESI."""
        token = self._get_token(character_id)
        if not token:
            return []

        import httpx

        response = httpx.get(
            f"https://esi.evetech.net/latest/characters/{character_id}/fittings/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        if response.status_code != 200:
            return []

        fittings = []
        for f in response.json():
            items = [
                FittingItem(
                    type_id=item["type_id"],
                    flag=item["flag"],
                    quantity=item["quantity"]
                )
                for item in f.get("items", [])
            ]
            fittings.append(ESIFitting(
                fitting_id=f.get("fitting_id"),
                name=f.get("name", "Unknown"),
                description=f.get("description", ""),
                ship_type_id=f.get("ship_type_id"),
                items=items
            ))

        return fittings

    def analyze_fitting_by_id(
        self,
        character_id: int,
        fitting_id: int,
        ammo_type_id: int,
        active_modules: Optional[List[int]] = None
    ) -> Optional[FittingAnalysis]:
        """Analyze a specific fitting by ID."""
        fittings = self.get_character_fittings(character_id)
        fitting = next((f for f in fittings if f.fitting_id == fitting_id), None)

        if not fitting:
            return None

        return self.analyze_fitting(
            fitting=fitting,
            character_id=character_id,
            ammo_type_id=ammo_type_id,
            active_modules=active_modules
        )

    def analyze_fitting(
        self,
        fitting: ESIFitting,
        character_id: int,
        ammo_type_id: int,
        active_modules: Optional[List[int]] = None
    ) -> FittingAnalysis:
        """Analyze a fitting for DPS with all modifiers."""
        active_modules = active_modules or []

        # Get ship name
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                (fitting.ship_type_id,)
            )
            ship_row = cur.fetchone()
            ship_name = ship_row["typeName"] if ship_row else "Unknown"

        # Get ammo name
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                (ammo_type_id,)
            )
            ammo_row = cur.fetchone()
            ammo_name = ammo_row["typeName"] if ammo_row else "Unknown"

        # Identify weapons in high slots (flags 27-34 are high slots)
        high_slot_items = [item for item in fitting.items if 27 <= item.flag <= 34]

        # Get weapon type IDs and check which are actual weapons
        weapon_items = []
        for item in high_slot_items:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if item is a weapon (has damage attributes)
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM "dgmTypeAttributes"
                        WHERE "typeID" = %s
                          AND "attributeID" IN (64, 114)  -- damageMultiplier, rateOfFire
                    ) as is_weapon
                """, (item.type_id,))
                result = cur.fetchone()
                if result and result["is_weapon"]:
                    weapon_items.append(item)

        weapon_count = sum(item.quantity for item in weapon_items)

        # Calculate base DPS per weapon
        base_dps = 0.0
        damage_breakdown = {"em": 0.0, "thermal": 0.0, "kinetic": 0.0, "explosive": 0.0}

        if weapon_items:
            # Get weapon stats
            weapon_type_id = weapon_items[0].type_id

            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                # Get weapon damage multiplier and rate of fire
                cur.execute("""
                    SELECT "attributeID", COALESCE("valueFloat", "valueInt") as value
                    FROM "dgmTypeAttributes"
                    WHERE "typeID" = %s
                      AND "attributeID" IN (64, 51, 30)
                """, (weapon_type_id,))

                weapon_attrs = {row["attributeID"]: row["value"] for row in cur.fetchall()}

                # Get ammo damage values
                cur.execute("""
                    SELECT "attributeID", COALESCE("valueFloat", "valueInt") as value
                    FROM "dgmTypeAttributes"
                    WHERE "typeID" = %s
                      AND "attributeID" IN (114, 116, 117, 118)
                """, (ammo_type_id,))

                ammo_attrs = {row["attributeID"]: row["value"] for row in cur.fetchall()}

            # Calculate damage per shot
            em_damage = ammo_attrs.get(114, 0)  # emDamage
            thermal_damage = ammo_attrs.get(118, 0)  # thermalDamage
            kinetic_damage = ammo_attrs.get(117, 0)  # kineticDamage
            explosive_damage = ammo_attrs.get(116, 0)  # explosiveDamage

            total_damage = em_damage + thermal_damage + kinetic_damage + explosive_damage

            # Get rate of fire (in milliseconds)
            rate_of_fire_ms = weapon_attrs.get(51, 5000)  # Default 5 seconds
            damage_multiplier = weapon_attrs.get(64, 1.0)

            # Calculate DPS for one weapon
            if rate_of_fire_ms > 0:
                shots_per_second = 1000.0 / rate_of_fire_ms
                dps_per_weapon = total_damage * damage_multiplier * shots_per_second

                base_dps = dps_per_weapon * weapon_count

                # Calculate damage breakdown
                damage_breakdown["em"] = (em_damage / total_damage * base_dps) if total_damage > 0 else 0
                damage_breakdown["thermal"] = (thermal_damage / total_damage * base_dps) if total_damage > 0 else 0
                damage_breakdown["kinetic"] = (kinetic_damage / total_damage * base_dps) if total_damage > 0 else 0
                damage_breakdown["explosive"] = (explosive_damage / total_damage * base_dps) if total_damage > 0 else 0

        # Calculate skill multiplier (simplified - would need character skills)
        skill_multiplier = 1.0

        # Calculate ship bonus multiplier
        ship_bonus_multiplier = 1.0

        # Check for Marauder class (gets 100% damage bonus from Bastion)
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE t."typeID" = %s
            """, (fitting.ship_type_id,))
            group_row = cur.fetchone()
            if group_row and group_row["groupName"] == "Marauder":
                ship_bonus_multiplier = 1.0  # Base, Bastion adds more

        # Calculate module bonus multiplier
        module_bonus_multiplier = 1.0
        active_module_names = []

        # Check for damage modules in low slots (flags 11-18)
        low_slot_items = [item for item in fitting.items if 11 <= item.flag <= 18]

        for item in low_slot_items:
            with self.db.cursor(cursor_factory=RealDictCursor) as cur:
                # Check for damage bonus attributes
                cur.execute("""
                    SELECT t."typeName",
                           COALESCE(dta."valueFloat", dta."valueInt") as damage_bonus
                    FROM "invTypes" t
                    LEFT JOIN "dgmTypeAttributes" dta ON dta."typeID" = t."typeID"
                        AND dta."attributeID" = 64  -- damageMultiplier
                    WHERE t."typeID" = %s
                """, (item.type_id,))
                result = cur.fetchone()

                if result and result["damage_bonus"]:
                    # Damage mods typically have a multiplier like 1.1 (10% bonus)
                    bonus = result["damage_bonus"]
                    if bonus > 1.0:
                        module_bonus_multiplier *= bonus

        # Check for Bastion Module in active modules
        BASTION_TYPE_IDS = [33400, 33402]  # Bastion Module I, II
        for mod_id in active_modules:
            if mod_id in BASTION_TYPE_IDS:
                module_bonus_multiplier *= 2.0  # Bastion doubles damage
                active_module_names.append("Bastion Module")

        # Calculate total DPS
        total_dps = base_dps * skill_multiplier * ship_bonus_multiplier * module_bonus_multiplier

        # Scale damage breakdown
        scale_factor = total_dps / base_dps if base_dps > 0 else 1.0
        final_breakdown = DamageBreakdown(
            em=damage_breakdown["em"] * scale_factor,
            thermal=damage_breakdown["thermal"] * scale_factor,
            kinetic=damage_breakdown["kinetic"] * scale_factor,
            explosive=damage_breakdown["explosive"] * scale_factor,
            total=total_dps
        )

        return FittingAnalysis(
            fitting_name=fitting.name,
            ship_type_id=fitting.ship_type_id,
            ship_name=ship_name,
            weapon_count=weapon_count,
            base_dps=round(base_dps, 2),
            skill_multiplier=round(skill_multiplier, 4),
            ship_bonus_multiplier=round(ship_bonus_multiplier, 4),
            module_bonus_multiplier=round(module_bonus_multiplier, 4),
            total_dps=round(total_dps, 2),
            damage_breakdown=final_breakdown,
            ammo_name=ammo_name,
            active_modules=active_module_names
        )
