"""Repository layer for tax profiles, facility profiles, and system cost indices."""
from typing import List, Optional

from app.models.tax import (
    TaxProfile,
    TaxProfileCreate,
    TaxProfileUpdate,
    FacilityProfile,
    FacilityProfileCreate,
    FacilityProfileUpdate,
    SystemCostIndex,
)


class TaxRepository:
    """Data access layer for tax profiles."""

    def __init__(self, db):
        """Initialize repository with database wrapper.

        Args:
            db: eve_shared database wrapper with cursor() context manager.
        """
        self.db = db

    def get_all(self, character_id: Optional[int] = None) -> List[TaxProfile]:
        """Get all tax profiles, optionally filtered by character.

        Args:
            character_id: Optional character ID to filter by. If None, returns
                         global profiles (where character_id IS NULL).

        Returns:
            List of TaxProfile objects.
        """
        with self.db.cursor() as cursor:
            if character_id is not None:
                cursor.execute(
                    """
                    SELECT id, name, character_id, broker_fee_buy, broker_fee_sell,
                           sales_tax, is_default, created_at, updated_at
                    FROM tax_profiles
                    WHERE character_id = %s OR character_id IS NULL
                    ORDER BY is_default DESC, name
                    """,
                    (character_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, name, character_id, broker_fee_buy, broker_fee_sell,
                           sales_tax, is_default, created_at, updated_at
                    FROM tax_profiles
                    WHERE character_id IS NULL
                    ORDER BY is_default DESC, name
                    """
                )
            rows = cursor.fetchall()
            return [self._row_to_profile(row) for row in rows]

    def get_by_id(self, profile_id: int) -> Optional[TaxProfile]:
        """Get tax profile by ID.

        Args:
            profile_id: The profile ID to look up.

        Returns:
            TaxProfile if found, None otherwise.
        """
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, character_id, broker_fee_buy, broker_fee_sell,
                       sales_tax, is_default, created_at, updated_at
                FROM tax_profiles
                WHERE id = %s
                """,
                (profile_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_profile(row)

    def get_default(self, character_id: Optional[int] = None) -> Optional[TaxProfile]:
        """Get the default tax profile for a character.

        Args:
            character_id: Optional character ID. If provided, returns character's
                         default or falls back to global default.

        Returns:
            Default TaxProfile if one exists, None otherwise.
        """
        with self.db.cursor() as cursor:
            if character_id is not None:
                # Try character-specific default first
                cursor.execute(
                    """
                    SELECT id, name, character_id, broker_fee_buy, broker_fee_sell,
                           sales_tax, is_default, created_at, updated_at
                    FROM tax_profiles
                    WHERE character_id = %s AND is_default = TRUE
                    LIMIT 1
                    """,
                    (character_id,)
                )
                row = cursor.fetchone()
                if row is not None:
                    return self._row_to_profile(row)
            # Fall back to global default
            cursor.execute(
                """
                SELECT id, name, character_id, broker_fee_buy, broker_fee_sell,
                       sales_tax, is_default, created_at, updated_at
                FROM tax_profiles
                WHERE character_id IS NULL AND is_default = TRUE
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_profile(row)

    def create(self, data: TaxProfileCreate) -> TaxProfile:
        """Create a new tax profile.

        Args:
            data: TaxProfileCreate with profile data.

        Returns:
            Created TaxProfile with assigned ID.
        """
        with self.db.cursor() as cursor:
            # If setting as default, unset other defaults first
            if data.is_default:
                cursor.execute(
                    "UPDATE tax_profiles SET is_default = FALSE WHERE is_default = TRUE"
                )

            cursor.execute(
                """
                INSERT INTO tax_profiles
                    (name, character_id, broker_fee_buy, broker_fee_sell, sales_tax, is_default)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, name, character_id, broker_fee_buy, broker_fee_sell,
                          sales_tax, is_default, created_at, updated_at
                """,
                (
                    data.name,
                    data.character_id,
                    data.broker_fee_buy,
                    data.broker_fee_sell,
                    data.sales_tax,
                    data.is_default,
                )
            )
            row = cursor.fetchone()
            return self._row_to_profile(row)

    def update(self, profile_id: int, data: TaxProfileUpdate) -> Optional[TaxProfile]:
        """Update an existing tax profile.

        Args:
            profile_id: The profile ID to update.
            data: TaxProfileUpdate with fields to update.

        Returns:
            Updated TaxProfile if found, None otherwise.
        """
        # Build dynamic update query from provided fields
        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.broker_fee_buy is not None:
            updates["broker_fee_buy"] = data.broker_fee_buy
        if data.broker_fee_sell is not None:
            updates["broker_fee_sell"] = data.broker_fee_sell
        if data.sales_tax is not None:
            updates["sales_tax"] = data.sales_tax
        if data.is_default is not None:
            updates["is_default"] = data.is_default

        if not updates:
            return self.get_by_id(profile_id)

        with self.db.cursor() as cursor:
            # If setting as default, unset other defaults first
            if updates.get("is_default"):
                cursor.execute(
                    "UPDATE tax_profiles SET is_default = FALSE WHERE is_default = TRUE"
                )

            set_clause = ", ".join(f"{key} = %s" for key in updates.keys())
            values = list(updates.values()) + [profile_id]

            cursor.execute(
                f"""
                UPDATE tax_profiles
                SET {set_clause}, updated_at = NOW()
                WHERE id = %s
                RETURNING id, name, character_id, broker_fee_buy, broker_fee_sell,
                          sales_tax, is_default, created_at, updated_at
                """,
                values
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_profile(row)

    def delete(self, profile_id: int) -> bool:
        """Delete a tax profile.

        Args:
            profile_id: The profile ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        with self.db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM tax_profiles WHERE id = %s",
                (profile_id,)
            )
            return cursor.rowcount > 0

    def _row_to_profile(self, row: tuple) -> TaxProfile:
        """Convert database row to TaxProfile model.

        Args:
            row: Tuple of (id, name, character_id, broker_fee_buy, broker_fee_sell,
                          sales_tax, is_default, created_at, updated_at).

        Returns:
            TaxProfile model instance.
        """
        return TaxProfile(
            id=row["id"],
            name=row["name"],
            character_id=row["character_id"],
            broker_fee_buy=row["broker_fee_buy"],
            broker_fee_sell=row["broker_fee_sell"],
            sales_tax=row["sales_tax"],
            is_default=row["is_default"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class FacilityRepository:
    """Data access layer for facility profiles."""

    def __init__(self, db):
        """Initialize repository with database wrapper.

        Args:
            db: eve_shared database wrapper with cursor() context manager.
        """
        self.db = db

    def get_all(self) -> List[FacilityProfile]:
        """Get all facility profiles.

        Returns:
            List of FacilityProfile objects.
        """
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT f.id, f.name, f.system_id, f.structure_type, f.me_bonus,
                       f.te_bonus, f.cost_bonus, f.facility_tax, f.reaction_me_bonus,
                       f.reaction_te_bonus, f.fuel_bonus, s."solarSystemName",
                       f.created_at, f.updated_at
                FROM facility_profiles f
                LEFT JOIN "mapSolarSystems" s ON f.system_id = s."solarSystemID"
                ORDER BY f.name
                """
            )
            rows = cursor.fetchall()
            return [self._row_to_facility(row) for row in rows]

    def get_by_id(self, facility_id: int) -> Optional[FacilityProfile]:
        """Get facility profile by ID.

        Args:
            facility_id: The facility ID to look up.

        Returns:
            FacilityProfile if found, None otherwise.
        """
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT f.id, f.name, f.system_id, f.structure_type, f.me_bonus,
                       f.te_bonus, f.cost_bonus, f.facility_tax, f.reaction_me_bonus,
                       f.reaction_te_bonus, f.fuel_bonus, s."solarSystemName",
                       f.created_at, f.updated_at
                FROM facility_profiles f
                LEFT JOIN "mapSolarSystems" s ON f.system_id = s."solarSystemID"
                WHERE f.id = %s
                """,
                (facility_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_facility(row)

    def create(self, data: FacilityProfileCreate) -> FacilityProfile:
        """Create a new facility profile.

        Args:
            data: FacilityProfileCreate with facility data.

        Returns:
            Created FacilityProfile with assigned ID.
        """
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO facility_profiles
                    (name, system_id, structure_type, me_bonus, te_bonus,
                     cost_bonus, facility_tax, reaction_me_bonus, reaction_te_bonus, fuel_bonus)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    data.name,
                    data.system_id,
                    data.structure_type,
                    data.me_bonus,
                    data.te_bonus,
                    data.cost_bonus,
                    data.facility_tax,
                    data.reaction_me_bonus,
                    data.reaction_te_bonus,
                    data.fuel_bonus,
                )
            )
            row = cursor.fetchone()
            facility_id = row["id"]
            return self.get_by_id(facility_id)

    def update(self, facility_id: int, data: FacilityProfileUpdate) -> Optional[FacilityProfile]:
        """Update an existing facility profile.

        Args:
            facility_id: The facility ID to update.
            data: FacilityProfileUpdate with fields to update.

        Returns:
            Updated FacilityProfile if found, None otherwise.
        """
        # Build dynamic update query from provided fields
        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.system_id is not None:
            updates["system_id"] = data.system_id
        if data.structure_type is not None:
            updates["structure_type"] = data.structure_type
        if data.me_bonus is not None:
            updates["me_bonus"] = data.me_bonus
        if data.te_bonus is not None:
            updates["te_bonus"] = data.te_bonus
        if data.cost_bonus is not None:
            updates["cost_bonus"] = data.cost_bonus
        if data.facility_tax is not None:
            updates["facility_tax"] = data.facility_tax
        if data.reaction_me_bonus is not None:
            updates["reaction_me_bonus"] = data.reaction_me_bonus
        if data.reaction_te_bonus is not None:
            updates["reaction_te_bonus"] = data.reaction_te_bonus
        if data.fuel_bonus is not None:
            updates["fuel_bonus"] = data.fuel_bonus

        if not updates:
            return self.get_by_id(facility_id)

        with self.db.cursor() as cursor:
            set_clause = ", ".join(f"{key} = %s" for key in updates.keys())
            values = list(updates.values()) + [facility_id]

            cursor.execute(
                f"""
                UPDATE facility_profiles
                SET {set_clause}, updated_at = NOW()
                WHERE id = %s
                """,
                values
            )
            if cursor.rowcount == 0:
                return None
            return self.get_by_id(facility_id)

    def delete(self, facility_id: int) -> bool:
        """Delete a facility profile.

        Args:
            facility_id: The facility ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        with self.db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM facility_profiles WHERE id = %s",
                (facility_id,)
            )
            return cursor.rowcount > 0

    def _row_to_facility(self, row: tuple) -> FacilityProfile:
        """Convert database row to FacilityProfile model.

        Args:
            row: Tuple of facility fields including joined system name.

        Returns:
            FacilityProfile model instance.
        """
        return FacilityProfile(
            id=row["id"],
            name=row["name"],
            system_id=row["system_id"],
            structure_type=row["structure_type"],
            me_bonus=row["me_bonus"],
            te_bonus=row["te_bonus"],
            cost_bonus=row["cost_bonus"],
            facility_tax=row["facility_tax"],
            reaction_me_bonus=row.get("reaction_me_bonus"),
            reaction_te_bonus=row.get("reaction_te_bonus"),
            fuel_bonus=row.get("fuel_bonus"),
            system_name=row.get("solarSystemName"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )


class SystemCostIndexRepository:
    """Data access layer for system cost indices from ESI."""

    def __init__(self, db):
        """Initialize repository with database wrapper.

        Args:
            db: eve_shared database wrapper with cursor() context manager.
        """
        self.db = db

    def get_by_system(self, system_id: int) -> Optional[SystemCostIndex]:
        """Get cost indices for a specific system.

        Args:
            system_id: The solar system ID.

        Returns:
            SystemCostIndex if found, None otherwise.
        """
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT sci.system_id, sci.system_name, sci.manufacturing_index,
                       sci.reaction_index, sci.copying_index, sci.invention_index,
                       sci.research_te_index, sci.research_me_index, sci.updated_at
                FROM system_cost_index sci
                WHERE sci.system_id = %s
                """,
                (system_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_index(row)

    def upsert(self, data: SystemCostIndex) -> SystemCostIndex:
        """Insert or update a system cost index.

        Args:
            data: SystemCostIndex with index data.

        Returns:
            Upserted SystemCostIndex.
        """
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO system_cost_index
                    (system_id, manufacturing_index, reaction_index, copying_index,
                     invention_index, research_te_index, research_me_index)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (system_id)
                DO UPDATE SET
                    manufacturing_index = EXCLUDED.manufacturing_index,
                    reaction_index = EXCLUDED.reaction_index,
                    copying_index = EXCLUDED.copying_index,
                    invention_index = EXCLUDED.invention_index,
                    research_te_index = EXCLUDED.research_te_index,
                    research_me_index = EXCLUDED.research_me_index,
                    updated_at = NOW()
                """,
                (
                    data.system_id,
                    data.manufacturing_index,
                    data.reaction_index,
                    data.copying_index,
                    data.invention_index,
                    data.research_te_index,
                    data.research_me_index,
                )
            )
            return self.get_by_system(data.system_id)

    def bulk_upsert(self, indices: List[SystemCostIndex]) -> int:
        """Bulk insert or update system cost indices.

        Args:
            indices: List of SystemCostIndex objects to upsert.

        Returns:
            Number of rows affected.
        """
        if not indices:
            return 0

        with self.db.cursor() as cursor:
            # Build VALUES list for bulk insert
            values = []
            for idx in indices:
                values.append((
                    idx.system_id,
                    idx.manufacturing_index,
                    idx.reaction_index,
                    idx.copying_index,
                    idx.invention_index,
                    idx.research_te_index,
                    idx.research_me_index,
                ))

            # Use executemany with ON CONFLICT
            cursor.executemany(
                """
                INSERT INTO system_cost_index
                    (system_id, manufacturing_index, reaction_index, copying_index,
                     invention_index, research_te_index, research_me_index)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (system_id)
                DO UPDATE SET
                    manufacturing_index = EXCLUDED.manufacturing_index,
                    reaction_index = EXCLUDED.reaction_index,
                    copying_index = EXCLUDED.copying_index,
                    invention_index = EXCLUDED.invention_index,
                    research_te_index = EXCLUDED.research_te_index,
                    research_me_index = EXCLUDED.research_me_index,
                    updated_at = NOW()
                """,
                values
            )
            return len(indices)

    def _row_to_index(self, row: tuple) -> SystemCostIndex:
        """Convert database row to SystemCostIndex model.

        Args:
            row: Tuple of index fields including joined system name.

        Returns:
            SystemCostIndex model instance.
        """
        return SystemCostIndex(
            system_id=row["system_id"],
            system_name=row["system_name"],
            manufacturing_index=row["manufacturing_index"],
            reaction_index=row["reaction_index"],
            copying_index=row["copying_index"],
            invention_index=row["invention_index"],
            research_te_index=row["research_te_index"],
            research_me_index=row["research_me_index"],
            updated_at=row["updated_at"],
        )
