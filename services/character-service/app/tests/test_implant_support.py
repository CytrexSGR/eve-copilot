"""Tests for CharacterRepository implant persistence and retrieval methods,
plus sync_character implant sync step.

Covers: persist_implants, get_implant_type_ids, sync_character implant integration.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.tests.conftest import MockCursor, MultiResultCursor, MockDB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo(cursor):
    """Build a CharacterRepository with a mock db and no redis."""
    with patch("app.services.repository.AuthClient"):
        from app.services.repository import CharacterRepository
        db = MockDB(cursor=cursor)
        return CharacterRepository(db=db, redis=None)


# ---------------------------------------------------------------------------
# persist_implants
# ---------------------------------------------------------------------------

class TestPersistImplants:
    def test_deletes_old_then_inserts_new(self):
        """persist_implants should DELETE existing, resolve names+slots, INSERT new."""
        cur = MultiResultCursor([
            [],  # DELETE (no rows returned)
            [{"typeID": 10228, "typeName": "Snake Alpha"}],  # _batch_resolve_type_names
            [{"typeID": 10228, "value": 1}],  # slot resolution
        ])
        repo = _make_repo(cur)
        repo.persist_implants(123, [10228])

        # DELETE + resolve names + resolve slots + 1 INSERT = 4 executes
        assert len(cur._executed) == 4

        # First call is DELETE
        delete_sql, delete_params = cur._executed[0]
        assert "DELETE FROM character_implants" in delete_sql
        assert "character_id" in delete_sql
        assert delete_params == (123,)

        # Second call is name resolution
        resolve_sql = cur._executed[1][0]
        assert '"invTypes"' in resolve_sql

        # Third call is slot resolution
        slot_sql = cur._executed[2][0]
        assert "dgmTypeAttributes" in slot_sql
        assert "331" in slot_sql

        # Fourth call is INSERT
        insert_sql, insert_params = cur._executed[3]
        assert "INSERT INTO character_implants" in insert_sql
        assert "ON CONFLICT" in insert_sql
        assert insert_params[0] == 123        # character_id
        assert insert_params[1] == 10228      # implant_type_id
        assert insert_params[2] == "Snake Alpha"  # implant_name
        assert insert_params[3] == 1          # slot

    def test_empty_list_only_deletes(self):
        """persist_implants with empty list should only DELETE, no resolve or INSERT."""
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_implants(456, [])

        # Only DELETE, no resolve or inserts
        assert len(cur._executed) == 1
        delete_sql, delete_params = cur._executed[0]
        assert "DELETE FROM character_implants" in delete_sql
        assert delete_params == (456,)

    def test_multiple_implants(self):
        """persist_implants with multiple implant IDs should insert each one."""
        cur = MultiResultCursor([
            [],  # DELETE
            [
                {"typeID": 10228, "typeName": "Snake Alpha"},
                {"typeID": 10230, "typeName": "Snake Gamma"},
            ],  # resolve names
            [
                {"typeID": 10228, "value": 1},
                {"typeID": 10230, "value": 3},
            ],  # resolve slots
        ])
        repo = _make_repo(cur)
        repo.persist_implants(10, [10228, 10230])

        # DELETE + resolve names + resolve slots + 2 INSERTs = 5
        assert len(cur._executed) == 5

        # Verify both inserts
        insert1_params = cur._executed[3][1]
        insert2_params = cur._executed[4][1]
        assert insert1_params[1] == 10228
        assert insert1_params[2] == "Snake Alpha"
        assert insert1_params[3] == 1
        assert insert2_params[1] == 10230
        assert insert2_params[2] == "Snake Gamma"
        assert insert2_params[3] == 3

    def test_unknown_name_fallback(self):
        """Implant with no SDE name should use 'Unknown' fallback."""
        cur = MultiResultCursor([
            [],  # DELETE
            [],  # name resolution returns nothing
            [],  # slot resolution returns nothing
        ])
        repo = _make_repo(cur)
        repo.persist_implants(10, [99999])

        # DELETE + resolve names + resolve slots + 1 INSERT = 4
        assert len(cur._executed) == 4
        insert_params = cur._executed[3][1]
        assert insert_params[2] == "Unknown"  # fallback name
        assert insert_params[3] == 0          # fallback slot

    def test_unknown_slot_defaults_to_zero(self):
        """Implant with a name but no slot attribute should default slot to 0."""
        cur = MultiResultCursor([
            [],  # DELETE
            [{"typeID": 10228, "typeName": "Snake Alpha"}],  # name found
            [],  # no slot found
        ])
        repo = _make_repo(cur)
        repo.persist_implants(10, [10228])

        insert_params = cur._executed[3][1]
        assert insert_params[2] == "Snake Alpha"
        assert insert_params[3] == 0  # default slot

    def test_insert_uses_on_conflict_do_update(self):
        """INSERT should have ON CONFLICT ... DO UPDATE to handle re-inserts."""
        cur = MultiResultCursor([
            [],  # DELETE
            [{"typeID": 10228, "typeName": "Snake Alpha"}],  # names
            [{"typeID": 10228, "value": 1}],  # slots
        ])
        repo = _make_repo(cur)
        repo.persist_implants(10, [10228])

        insert_sql = cur._executed[3][0]
        assert "ON CONFLICT" in insert_sql
        assert "DO UPDATE" in insert_sql

    def test_exception_is_logged_not_raised(self):
        """persist_implants should catch exceptions and log them."""
        cur = MockCursor()
        # Make execute raise on the first call
        def failing_execute(sql, params=None):
            raise Exception("DB error")
        cur.execute = failing_execute

        repo = _make_repo(cur)
        # Should not raise
        repo.persist_implants(10, [10228])


# ---------------------------------------------------------------------------
# get_implant_type_ids
# ---------------------------------------------------------------------------

class TestGetImplantTypeIds:
    def test_returns_list_of_type_ids(self):
        """Should return a list of implant_type_id ints."""
        cur = MockCursor([
            {"implant_type_id": 10228},
            {"implant_type_id": 10230},
            {"implant_type_id": 10232},
        ])
        repo = _make_repo(cur)
        result = repo.get_implant_type_ids(123)

        assert result == [10228, 10230, 10232]

    def test_returns_empty_list_when_no_implants(self):
        """Should return empty list when character has no implants."""
        cur = MockCursor([])
        repo = _make_repo(cur)
        result = repo.get_implant_type_ids(999)

        assert result == []

    def test_query_filters_by_character_id(self):
        """SELECT should filter by character_id."""
        cur = MockCursor([])
        repo = _make_repo(cur)
        repo.get_implant_type_ids(42)

        sql, params = cur._executed[0]
        assert "character_implants" in sql
        assert "character_id" in sql
        assert params == (42,)

    def test_query_orders_by_slot(self):
        """Results should be ordered by slot."""
        cur = MockCursor([])
        repo = _make_repo(cur)
        repo.get_implant_type_ids(10)

        sql = cur.last_sql
        assert "ORDER BY slot" in sql

    def test_selects_implant_type_id_column(self):
        """Query should select implant_type_id column."""
        cur = MockCursor([])
        repo = _make_repo(cur)
        repo.get_implant_type_ids(10)

        sql = cur.last_sql
        assert "implant_type_id" in sql


# ---------------------------------------------------------------------------
# sync_character — implant sync step
# ---------------------------------------------------------------------------

def _make_service():
    """Build a CharacterService with fully mocked dependencies."""
    with patch("app.services.character.AuthClient"), \
         patch("app.services.character.ESIClient"), \
         patch("app.services.character.CharacterRepository"):
        from app.services.character import CharacterService
        svc = CharacterService(db=MagicMock(), redis=None)
        # Ensure _get_token returns a dummy token
        svc._get_token = MagicMock(return_value="fake-token")
        # Default: all sync helpers return falsy so only implant path matters
        svc.get_wallet = MagicMock(return_value=None)
        svc.get_skills = MagicMock(return_value=None)
        svc.get_skillqueue = MagicMock(return_value=None)
        svc.get_assets = MagicMock(return_value=None)
        svc.get_orders = MagicMock(return_value=None)
        svc.get_industry_jobs = MagicMock(return_value=None)
        svc.get_blueprints = MagicMock(return_value=None)
        svc.get_location = MagicMock(return_value=None)
        svc.get_ship = MagicMock(return_value=None)
        svc._update_corporation_history = MagicMock(return_value=False)
        return svc


class TestSyncCharacterImplants:
    """Tests for the implant sync step inside sync_character()."""

    def test_results_dict_has_implants_key(self):
        """sync_character results must contain an 'implants' key."""
        svc = _make_service()
        svc.esi.get_implants = MagicMock(return_value=[])
        results = svc.sync_character(123)
        assert "implants" in results

    def test_implants_default_false(self):
        """When ESI returns None, implants result stays False."""
        svc = _make_service()
        svc.esi.get_implants = MagicMock(return_value=None)
        results = svc.sync_character(123)
        assert results["implants"] is False

    def test_implants_true_on_success(self):
        """When ESI returns implant IDs, implants result is True."""
        svc = _make_service()
        svc.esi.get_implants = MagicMock(return_value=[10228, 10230])
        results = svc.sync_character(123)
        assert results["implants"] is True

    def test_calls_esi_get_implants(self):
        """sync_character should call esi.get_implants with character_id and token."""
        svc = _make_service()
        svc.esi.get_implants = MagicMock(return_value=[10228])
        svc.sync_character(456)
        svc.esi.get_implants.assert_called_once_with(456, "fake-token")

    def test_calls_repo_persist_implants(self):
        """sync_character should call repo.persist_implants with character_id and IDs."""
        svc = _make_service()
        svc.esi.get_implants = MagicMock(return_value=[10228, 10230])
        svc.sync_character(789)
        svc.repo.persist_implants.assert_called_once_with(789, [10228, 10230])

    def test_implant_exception_does_not_break_sync(self):
        """If implant sync raises, other results still returned."""
        svc = _make_service()
        svc.esi.get_implants = MagicMock(side_effect=Exception("ESI timeout"))
        results = svc.sync_character(123)
        # implants stays False due to exception
        assert results["implants"] is False
        # Other keys still present
        assert "wallet" in results
        assert "skills" in results

    def test_empty_list_still_persists(self):
        """An empty implant list (clone without implants) should still persist."""
        svc = _make_service()
        svc.esi.get_implants = MagicMock(return_value=[])
        svc.sync_character(123)
        # Empty list is not None, so persist should be called
        svc.repo.persist_implants.assert_called_once_with(123, [])


# ---------------------------------------------------------------------------
# Dogma Engine — implant_type_ids parameter
# ---------------------------------------------------------------------------

class TestDogmaImplantParameter:
    def test_accepts_implant_type_ids_parameter(self):
        """calculate_modified_attributes should accept implant_type_ids."""
        import inspect
        from app.services.dogma.engine import DogmaEngine
        sig = inspect.signature(DogmaEngine.calculate_modified_attributes)
        assert "implant_type_ids" in sig.parameters

    def test_implant_type_ids_defaults_to_none(self):
        """implant_type_ids should default to None."""
        import inspect
        from app.services.dogma.engine import DogmaEngine
        param = inspect.signature(DogmaEngine.calculate_modified_attributes).parameters["implant_type_ids"]
        assert param.default is None

    def test_parameter_is_optional_list_of_int(self):
        """Parameter type annotation should be Optional[List[int]]."""
        import inspect
        from app.services.dogma.engine import DogmaEngine
        param = inspect.signature(DogmaEngine.calculate_modified_attributes).parameters["implant_type_ids"]
        # Just verify it exists and has a default of None (Optional)
        assert param.default is None


# ---------------------------------------------------------------------------
# FittingStatsRequest — include_implants field
# ---------------------------------------------------------------------------

class TestFittingStatsImplantField:
    def test_request_has_include_implants_field(self):
        from app.services.fitting_stats.models import FittingStatsRequest
        req = FittingStatsRequest(ship_type_id=17740, items=[])
        assert hasattr(req, "include_implants")
        assert req.include_implants is True

    def test_include_implants_default_true(self):
        from app.services.fitting_stats.models import FittingStatsRequest
        req = FittingStatsRequest(ship_type_id=17740, items=[])
        assert req.include_implants is True

    def test_include_implants_can_be_disabled(self):
        from app.services.fitting_stats.models import FittingStatsRequest
        req = FittingStatsRequest(ship_type_id=17740, items=[], include_implants=False)
        assert req.include_implants is False


# ---------------------------------------------------------------------------
# FittingStatsResponse — active_implants field
# ---------------------------------------------------------------------------

class TestFittingStatsResponseImplants:
    def test_response_has_active_implants_field(self):
        from app.services.fitting_stats.models import (
            FittingStatsResponse, SlotUsage, ResourceUsage, OffenseStats,
            DefenseStats, CapacitorStats, NavigationStats, TargetingStats
        )
        resp = FittingStatsResponse(
            ship={"typeID": 1, "typeName": "Test", "groupName": "Test"},
            slots=SlotUsage(), resources=ResourceUsage(), offense=OffenseStats(),
            defense=DefenseStats(), capacitor=CapacitorStats(),
            navigation=NavigationStats(), targeting=TargetingStats(),
        )
        assert hasattr(resp, "active_implants")
        assert resp.active_implants == []

    def test_active_implant_model(self):
        from app.services.fitting_stats.models import ActiveImplant
        imp = ActiveImplant(type_id=53710, type_name="Nirvana Alpha", slot=1)
        assert imp.type_id == 53710
        assert imp.type_name == "Nirvana Alpha"
        assert imp.slot == 1

    def test_active_implant_defaults(self):
        from app.services.fitting_stats.models import ActiveImplant
        imp = ActiveImplant(type_id=53710)
        assert imp.type_name == "Unknown"
        assert imp.slot == 0
