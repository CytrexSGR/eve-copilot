"""Structure Bonus Calculator.

Calculates material and time modifiers for Engineering Complex
structures with installed rigs and security scaling.

EVE Online formula:
  quantity = max(1, ceil(base_qty * (1 - ME/100) * structure_mult * rig_mult))

Security scaling for rig bonuses:
  Highsec:   1.0x
  Lowsec:    1.9x
  Nullsec:   2.1x
  Wormhole:  2.1x
"""

import logging
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

# Security multipliers for rig bonuses
SECURITY_SCALING = {
    "high": Decimal("1.0"),
    "low": Decimal("1.9"),
    "null": Decimal("2.1"),
    "wh": Decimal("2.1"),
}


class StructureBonusCalculator:
    """Calculates combined structure + rig bonuses for production."""

    def __init__(self, db):
        self.db = db

    def get_facility(self, facility_id: int) -> Optional[dict]:
        """Fetch a facility profile by ID."""
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT * FROM facility_profiles WHERE id = %s",
                (facility_id,),
            )
            return cur.fetchone()

    def get_material_modifier(self, facility_id: int) -> float:
        """Get the combined material modifier for a facility.

        Returns a multiplier to apply to base materials AFTER ME:
          quantity = ceil(base * me_factor * material_modifier)

        structure_me_bonus of 1% means 0.99 multiplier.
        rig_me_bonus of 4.2% means 0.958 multiplier (in nullsec: 4.2 * 2.1 = 8.82% → 0.9118).
        """
        facility = self.get_facility(facility_id)
        if not facility:
            return 1.0

        # Structure base bonus
        structure_me = Decimal(str(facility.get("me_bonus", 0)))
        structure_modifier = Decimal("1") - (structure_me / Decimal("100"))

        # Rig bonus with security scaling
        rig_me = Decimal(str(facility.get("rig_me_bonus", 0)))
        security = facility.get("security", "high")
        sec_mult = SECURITY_SCALING.get(security, Decimal("1.0"))
        rig_modifier = Decimal("1") - (rig_me * sec_mult / Decimal("100"))

        combined = float(structure_modifier * rig_modifier)
        return max(0.0, combined)

    def get_time_modifier(self, facility_id: int) -> float:
        """Get the combined time modifier for a facility.

        Returns a multiplier to apply to base production time AFTER TE:
          time = base_time * te_factor * time_modifier
        """
        facility = self.get_facility(facility_id)
        if not facility:
            return 1.0

        structure_te = Decimal(str(facility.get("te_bonus", 0)))
        structure_modifier = Decimal("1") - (structure_te / Decimal("100"))

        rig_te = Decimal(str(facility.get("rig_te_bonus", 0)))
        security = facility.get("security", "high")
        sec_mult = SECURITY_SCALING.get(security, Decimal("1.0"))
        rig_modifier = Decimal("1") - (rig_te * sec_mult / Decimal("100"))

        combined = float(structure_modifier * rig_modifier)
        return max(0.0, combined)

    def get_cost_modifier(self, facility_id: int) -> float:
        """Get the cost modifier (tax/fee reduction) for a facility."""
        facility = self.get_facility(facility_id)
        if not facility:
            return 1.0

        cost_bonus = Decimal(str(facility.get("cost_bonus", 0)))
        return float(Decimal("1") - (cost_bonus / Decimal("100")))

    def get_facility_tax(self, facility_id: int) -> float:
        """Get the facility tax rate."""
        facility = self.get_facility(facility_id)
        if not facility:
            return 0.10  # NPC default 10%

        return float(facility.get("facility_tax", 0)) / 100.0
