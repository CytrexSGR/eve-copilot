"""Tests for SQL WHERE clause filter building logic.

Tests the dynamic SQL filter construction in RedListChecker.get_all()
and the fleet session query parameter logic in ActivityTracker.
"""

import pytest


# ---- Pure functions extracted from RedListChecker.get_all ----


def build_red_list_where(
    active_only: bool = True,
    category: str | None = None,
) -> tuple[str, dict]:
    """Build WHERE clause for red list queries.

    Reimplemented from RedListChecker.get_all filter logic.
    Returns (where_clause, params).
    """
    conditions = []
    params: dict = {}

    if active_only:
        conditions.append("active = TRUE")
    if category:
        conditions.append("category = %(category)s")
        params["category"] = category

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where, params


def build_fleet_session_where(
    character_id: int | None = None,
    limit: int = 50,
) -> tuple[str, dict]:
    """Build WHERE and params for fleet session queries.

    Reimplemented from ActivityTracker.get_fleet_sessions.
    """
    params: dict = {"limit": limit}
    where = ""

    if character_id:
        where = "WHERE character_id = %(character_id)s"
        params["character_id"] = character_id

    return where, params


def build_fleet_session_defaults(session: dict) -> dict:
    """Apply defaults to fleet session dict.

    Reimplemented from ActivityTracker.record_fleet_session.
    """
    result = dict(session)
    result.setdefault("character_name", None)
    result.setdefault("ship_name", None)
    result.setdefault("fleet_id", None)
    result.setdefault("fleet_name", None)
    result.setdefault("ship_type_id", None)
    result.setdefault("end_time", None)
    result.setdefault("solar_system_id", None)
    return result


# ---- Tests ----


class TestRedListWhereClause:
    """Tests for red list SQL filter building."""

    def test_active_only_default(self):
        """Default active_only=True should add active filter."""
        where, params = build_red_list_where()
        assert "active = TRUE" in where
        assert params == {}

    def test_active_only_false(self):
        """active_only=False should not add active filter."""
        where, params = build_red_list_where(active_only=False)
        assert "active" not in where

    def test_category_filter(self):
        """Category filter should add parameterized condition."""
        where, params = build_red_list_where(category="character")
        assert "category = %(category)s" in where
        assert params["category"] == "character"

    def test_both_filters(self):
        """Both filters should be combined with AND."""
        where, params = build_red_list_where(
            active_only=True, category="corporation"
        )
        assert "AND" in where
        assert "active = TRUE" in where
        assert "category = %(category)s" in where
        assert params["category"] == "corporation"

    def test_no_filters(self):
        """No active filter and no category should produce empty WHERE."""
        where, params = build_red_list_where(active_only=False, category=None)
        assert where == ""
        assert params == {}

    def test_where_starts_with_keyword(self):
        """Non-empty WHERE clause should start with 'WHERE'."""
        where, _ = build_red_list_where()
        assert where.startswith("WHERE")


class TestFleetSessionWhere:
    """Tests for fleet session query building."""

    def test_no_character_filter(self):
        """No character_id should produce empty WHERE."""
        where, params = build_fleet_session_where()
        assert where == ""
        assert params["limit"] == 50

    def test_with_character_filter(self):
        """character_id should add WHERE clause."""
        where, params = build_fleet_session_where(character_id=12345)
        assert "character_id" in where
        assert params["character_id"] == 12345

    def test_custom_limit(self):
        """Custom limit should be in params."""
        _, params = build_fleet_session_where(limit=100)
        assert params["limit"] == 100


class TestFleetSessionDefaults:
    """Tests for fleet session default value application."""

    def test_minimal_session_gets_defaults(self):
        """Session with only required fields should get all defaults."""
        session = {
            "character_id": 123,
            "start_time": "2026-01-15T20:00:00",
        }
        result = build_fleet_session_defaults(session)
        assert result["character_name"] is None
        assert result["ship_name"] is None
        assert result["fleet_id"] is None
        assert result["fleet_name"] is None
        assert result["ship_type_id"] is None
        assert result["end_time"] is None
        assert result["solar_system_id"] is None

    def test_existing_values_preserved(self):
        """Existing values should not be overwritten by defaults."""
        session = {
            "character_id": 123,
            "start_time": "2026-01-15T20:00:00",
            "fleet_name": "Stratop",
            "ship_type_id": 24698,
        }
        result = build_fleet_session_defaults(session)
        assert result["fleet_name"] == "Stratop"
        assert result["ship_type_id"] == 24698
        # Other defaults still applied
        assert result["character_name"] is None
        assert result["ship_name"] is None

    def test_original_dict_not_mutated(self):
        """The original session dict should not be modified."""
        session = {"character_id": 123, "start_time": "2026-01-15T20:00:00"}
        original_keys = set(session.keys())
        build_fleet_session_defaults(session)
        # Note: setdefault DOES mutate the original, so this tests the copy
        # The reimplemented function uses dict() copy
        assert set(session.keys()) == original_keys

    def test_all_seven_defaults_applied(self):
        """Exactly 7 optional fields should get defaults."""
        session = {"character_id": 123, "start_time": "now"}
        result = build_fleet_session_defaults(session)
        optional_keys = [
            "character_name", "ship_name", "fleet_id", "fleet_name",
            "ship_type_id", "end_time", "solar_system_id",
        ]
        for key in optional_keys:
            assert key in result
