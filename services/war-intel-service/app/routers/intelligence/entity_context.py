"""Entity context for parameterized SQL queries across Alliance, Corporation, and PowerBloc."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityType(Enum):
    ALLIANCE = "alliance"
    CORPORATION = "corporation"
    POWERBLOC = "powerbloc"


@dataclass
class EntityContext:
    """Parameterizes SQL queries for different entity types.

    Alliance:   Single alliance_id, kills via c.alliance_id, deaths via c.alliance_id
    Corporation: Single corp_id, kills via ka.corporation_id, deaths via km.victim_corporation_id
    PowerBloc:  List of alliance_ids, kills via c.alliance_id = ANY(), deaths via c.alliance_id = ANY()
    """
    entity_type: EntityType
    entity_id: int | None = None
    member_ids: list[int] | None = None
    alliance_id_for_sov: Any = None  # For corporation: the corp's alliance_id

    # --- Kill filters ---

    @property
    def kill_attacker_filter(self) -> str:
        """WHERE clause for identifying kills (attacker side)."""
        if self.entity_type == EntityType.CORPORATION:
            return "ka.corporation_id = %s"
        elif self.entity_type == EntityType.POWERBLOC:
            return "c.alliance_id = ANY(%s)"
        else:
            return "c.alliance_id = %s"

    @property
    def kill_attacker_needs_corp_join(self) -> bool:
        """Whether kills query needs JOIN corporations c ON ka.corporation_id = c.corporation_id."""
        return self.entity_type != EntityType.CORPORATION

    # --- Death filters ---

    @property
    def death_victim_filter(self) -> str:
        """WHERE clause for identifying deaths (victim side)."""
        if self.entity_type == EntityType.CORPORATION:
            return "km.victim_corporation_id = %s"
        elif self.entity_type == EntityType.POWERBLOC:
            return "c.alliance_id = ANY(%s)"
        else:
            return "c.alliance_id = %s"

    @property
    def death_victim_needs_corp_join(self) -> bool:
        """Whether deaths query needs JOIN corporations c ON km.victim_corporation_id = c.corporation_id."""
        return self.entity_type != EntityType.CORPORATION

    # --- Sovereignty check ---

    @property
    def sov_filter(self) -> str:
        """Sovereignty ownership check."""
        if self.entity_type == EntityType.POWERBLOC:
            return "sov.alliance_id = ANY(%s)"
        else:
            return "sov.alliance_id = %s"

    # --- Parameter helpers ---

    @property
    def filter_value(self) -> Any:
        """The value to bind in SQL queries."""
        if self.entity_type == EntityType.POWERBLOC:
            return self.member_ids
        return self.entity_id

    @property
    def sov_value(self) -> Any:
        """The value for sovereignty checks."""
        if self.entity_type == EntityType.CORPORATION:
            return self.alliance_id_for_sov
        return self.filter_value

    def kill_params(self, days: int) -> tuple:
        """Parameters for a kill query: (filter_value, days)."""
        return (self.filter_value, days)

    def death_params(self, days: int) -> tuple:
        """Parameters for a death query: (filter_value, days)."""
        return (self.filter_value, days)

    def region_params(self, days: int) -> tuple:
        """Parameters for region query (kills + deaths): (kill_val, days, death_val, days)."""
        return (self.filter_value, days, self.filter_value, days)

    def home_params(self, days: int) -> tuple:
        """Parameters for home systems query: (kill_val, days, death_val, days, sov_val)."""
        return (self.filter_value, days, self.filter_value, days, self.sov_value)

    # --- Capital-specific filters (use ka.alliance_id / km.victim_alliance_id) ---

    @property
    def capital_kill_filter(self) -> str:
        """WHERE clause for capital kills (attacker side, named params)."""
        if self.entity_type == EntityType.CORPORATION:
            return "ka.corporation_id = %(entity_id)s"
        elif self.entity_type == EntityType.POWERBLOC:
            return "ka.alliance_id = ANY(%(entity_id)s)"
        else:
            return "ka.alliance_id = %(entity_id)s"

    @property
    def capital_loss_filter(self) -> str:
        """WHERE clause for capital losses (victim side, named params)."""
        if self.entity_type == EntityType.CORPORATION:
            return "km.victim_corporation_id = %(entity_id)s"
        elif self.entity_type == EntityType.POWERBLOC:
            return "km.victim_alliance_id = ANY(%(entity_id)s)"
        else:
            return "km.victim_alliance_id = %(entity_id)s"

    @property
    def capital_recent_attacker_filter(self) -> str:
        """Filter for recent activity kills JOIN (named params)."""
        if self.entity_type == EntityType.CORPORATION:
            return "ka.corporation_id = %(entity_id)s"
        elif self.entity_type == EntityType.POWERBLOC:
            return "ka.alliance_id = ANY(%(entity_id)s)"
        else:
            return "ka.alliance_id = %(entity_id)s"

    @property
    def capital_sql_params(self) -> dict:
        """Named parameters dict for capital queries."""
        return {"entity_id": self.filter_value}
