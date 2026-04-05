"""Tests for CharacterRepository persistence, batch read, and sync-status methods.

Covers: persist_wallet, persist_skills, persist_skillqueue, persist_location,
persist_ship, persist_orders, persist_industry_jobs, update_sync_status,
_batch_resolve_type_names, _batch_resolve_station_names, get_all_summaries_from_db.
"""

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import datetime

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
# persist_wallet
# ---------------------------------------------------------------------------

class TestPersistWallet:
    def test_inserts_with_correct_params(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_wallet(123, 5_000_000.50)

        assert len(cur._executed) == 1
        sql, params = cur._executed[0]
        assert "INSERT INTO character_wallets" in sql
        assert params == (123, 5_000_000.50)

    def test_on_conflict_do_nothing(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_wallet(1, 0)

        sql = cur.last_sql
        assert "ON CONFLICT" in sql
        assert "DO NOTHING" in sql

    def test_zero_balance(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_wallet(99, 0.0)

        assert cur.last_params == (99, 0.0)


# ---------------------------------------------------------------------------
# persist_skills
# ---------------------------------------------------------------------------

class TestPersistSkills:
    def test_inserts_one_skill(self):
        # First execute resolves names, then one insert per skill
        cur = MultiResultCursor([
            [{"typeID": 3300, "typeName": "Gunnery"}],  # _batch_resolve_type_names
        ])
        repo = _make_repo(cur)
        repo.persist_skills(10, [
            {"skill_id": 3300, "active_skill_level": 5,
             "trained_skill_level": 5, "skillpoints_in_skill": 256000}
        ])

        # 1 resolve query + 1 insert = 2 execute calls
        assert len(cur._executed) == 2
        insert_sql, insert_params = cur._executed[1]
        assert "INSERT INTO character_skills" in insert_sql
        assert "ON CONFLICT" in insert_sql
        assert insert_params[0] == 10       # character_id
        assert insert_params[1] == 3300     # skill_id
        assert insert_params[2] == "Gunnery"  # resolved name

    def test_multiple_skills(self):
        cur = MultiResultCursor([
            [{"typeID": 100, "typeName": "SkillA"}, {"typeID": 200, "typeName": "SkillB"}],
        ])
        repo = _make_repo(cur)
        repo.persist_skills(10, [
            {"skill_id": 100, "active_skill_level": 1,
             "trained_skill_level": 1, "skillpoints_in_skill": 100},
            {"skill_id": 200, "active_skill_level": 2,
             "trained_skill_level": 2, "skillpoints_in_skill": 200},
        ])

        # 1 resolve + 2 inserts
        assert len(cur._executed) == 3

    def test_empty_skills_list(self):
        cur = MultiResultCursor([
            [],  # empty resolve
        ])
        repo = _make_repo(cur)
        repo.persist_skills(10, [])

        # Only the resolve query with empty list (short-circuited)
        # _batch_resolve_type_names returns {} for empty input without executing
        assert len(cur._executed) == 0

    def test_unknown_skill_name_fallback(self):
        cur = MultiResultCursor([
            [],  # empty resolve result — name not found
        ])
        repo = _make_repo(cur)
        repo.persist_skills(10, [
            {"skill_id": 9999, "active_skill_level": 1,
             "trained_skill_level": 1, "skillpoints_in_skill": 0}
        ])

        # resolve returned nothing, but _batch_resolve_type_names gets empty []
        # since skill_ids=[9999] is non-empty, it runs the query
        insert_sql, insert_params = cur._executed[1]
        assert insert_params[2] == "Unknown"  # fallback name


# ---------------------------------------------------------------------------
# persist_skillqueue
# ---------------------------------------------------------------------------

class TestPersistSkillqueue:
    def test_deletes_before_inserting(self):
        cur = MultiResultCursor([
            [{"typeID": 500, "typeName": "Navigation"}],  # resolve
        ])
        repo = _make_repo(cur)
        repo.persist_skillqueue(10, [
            {"skill_id": 500, "queue_position": 0, "finished_level": 4}
        ])

        # 1 resolve + 1 DELETE + 1 INSERT = 3
        assert len(cur._executed) == 3
        assert "DELETE FROM character_skill_queue" in cur._executed[1][0]
        assert "INSERT INTO character_skill_queue" in cur._executed[2][0]

    def test_delete_uses_character_id(self):
        cur = MultiResultCursor([[]])
        repo = _make_repo(cur)
        repo.persist_skillqueue(42, [])

        # Empty queue_list: resolve (empty, skipped) + DELETE only
        assert len(cur._executed) == 1
        delete_sql, delete_params = cur._executed[0]
        assert "DELETE" in delete_sql
        assert delete_params == (42,)

    def test_insert_queue_item_fields(self):
        cur = MultiResultCursor([
            [{"typeID": 600, "typeName": "Warp Drive Op"}],
        ])
        repo = _make_repo(cur)
        repo.persist_skillqueue(10, [
            {"skill_id": 600, "queue_position": 2, "finished_level": 3,
             "start_date": "2026-01-01T00:00:00Z", "finish_date": "2026-01-02T00:00:00Z",
             "training_start_sp": 100, "level_start_sp": 50, "level_end_sp": 500}
        ])

        insert_sql, insert_params = cur._executed[2]
        assert insert_params[0] == 10   # character_id
        assert insert_params[1] == 2    # queue_position
        assert insert_params[2] == 600  # skill_id
        assert insert_params[3] == "Warp Drive Op"


# ---------------------------------------------------------------------------
# persist_location
# ---------------------------------------------------------------------------

class TestPersistLocation:
    def test_inserts_with_on_conflict(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_location(10, {
            "solar_system_id": 30000142,
            "station_id": 60003760,
            "structure_id": None,
        })

        assert len(cur._executed) == 1
        sql, params = cur._executed[0]
        assert "INSERT INTO character_location" in sql
        assert "ON CONFLICT (character_id) DO UPDATE" in sql
        assert params[0] == 10
        assert params[1] == 30000142
        assert params[2] == 60003760
        assert params[3] is None

    def test_missing_fields_default_none(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_location(10, {})

        params = cur.last_params
        assert params == (10, None, None, None)


# ---------------------------------------------------------------------------
# persist_ship
# ---------------------------------------------------------------------------

class TestPersistShip:
    def test_inserts_with_on_conflict(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_ship(10, {
            "ship_item_id": 1234567,
            "ship_type_id": 24698,
            "ship_name": "My Drake",
            "ship_type_name": "Drake",
        })

        sql, params = cur._executed[0]
        assert "INSERT INTO character_ship" in sql
        assert "ON CONFLICT (character_id) DO UPDATE" in sql
        assert params == (10, 1234567, 24698, "My Drake", "Drake")

    def test_empty_ship_dict(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_ship(10, {})

        params = cur.last_params
        assert params == (10, None, None, None, None)


# ---------------------------------------------------------------------------
# persist_orders
# ---------------------------------------------------------------------------

class TestPersistOrders:
    def test_marks_existing_as_expired_then_inserts(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        orders = [
            {
                "order_id": 555, "type_id": 34, "type_name": "Tritanium",
                "location_id": 60003760, "location_name": "Jita 4-4",
                "region_id": 10000002, "is_buy_order": False, "price": 5.0,
                "volume_total": 1000, "volume_remain": 500, "min_volume": 1,
                "range": "station", "duration": 90, "escrow": 0,
                "is_corporation": False, "issued": "2026-01-01T00:00:00Z",
            }
        ]
        repo.persist_orders(10, orders)

        # 1 UPDATE (expire) + 1 INSERT = 2
        assert len(cur._executed) == 2
        expire_sql = cur._executed[0][0]
        assert "UPDATE character_orders SET state = 'expired'" in expire_sql
        assert cur._executed[0][1] == (10,)

        insert_sql = cur._executed[1][0]
        assert "INSERT INTO character_orders" in insert_sql
        assert "'active'" in insert_sql

    def test_uses_model_type_name(self):
        """Orders should use pre-resolved type_name from model, not SDE lookup."""
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_orders(10, [
            {"order_id": 1, "type_id": 34, "type_name": "Tritanium",
             "location_id": 60003760, "location_name": "Jita 4-4",
             "region_id": 10000002, "is_buy_order": True, "price": 4.0,
             "volume_total": 100, "volume_remain": 50}
        ])

        insert_params = cur._executed[1][1]
        # type_name is the 4th param (index 3)
        assert insert_params[3] == "Tritanium"

    def test_uses_model_location_name(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_orders(10, [
            {"order_id": 2, "type_id": 35, "type_name": "Pyerite",
             "location_id": 60003760, "location_name": "Jita 4-4",
             "region_id": 10000002}
        ])

        insert_params = cur._executed[1][1]
        # location_name is the 6th param (index 5)
        assert insert_params[5] == "Jita 4-4"

    def test_empty_orders(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_orders(10, [])

        # Only the expire UPDATE, no inserts
        assert len(cur._executed) == 1
        assert "UPDATE" in cur._executed[0][0]

    def test_default_region_id(self):
        """Missing region_id should default to 10000002 (The Forge)."""
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.persist_orders(10, [
            {"order_id": 3, "type_id": 34, "type_name": "Tritanium",
             "location_id": 60003760, "location_name": "Jita"}
        ])

        insert_params = cur._executed[1][1]
        # region_id is 7th param (index 6)
        assert insert_params[6] == 10000002


# ---------------------------------------------------------------------------
# persist_industry_jobs
# ---------------------------------------------------------------------------

class TestPersistIndustryJobs:
    def test_resolves_type_names_and_inserts(self):
        cur = MultiResultCursor([
            [{"typeID": 1000, "typeName": "Blueprint A"},
             {"typeID": 2000, "typeName": "Product B"}],
        ])
        repo = _make_repo(cur)
        repo.persist_industry_jobs(10, [
            {"job_id": 1, "blueprint_type_id": 1000, "product_type_id": 2000,
             "activity_id": 1, "blueprint_id": 500, "status": "active",
             "start_date": "2026-01-01", "end_date": "2026-01-02"}
        ])

        # 1 resolve + 1 insert
        assert len(cur._executed) == 2
        insert_sql, insert_params = cur._executed[1]
        assert "INSERT INTO character_industry_jobs" in insert_sql
        assert "ON CONFLICT" in insert_sql
        # blueprint_type_name = resolved
        assert insert_params[7] == "Blueprint A"
        # product_type_name = resolved
        assert insert_params[11] == "Product B"

    def test_empty_jobs_list(self):
        cur = MultiResultCursor([[]])
        repo = _make_repo(cur)
        repo.persist_industry_jobs(10, [])

        # No type_ids to resolve (empty set), no inserts
        assert len(cur._executed) == 0


# ---------------------------------------------------------------------------
# update_sync_status
# ---------------------------------------------------------------------------

class TestUpdateSyncStatus:
    def test_only_updates_successful_syncs(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.update_sync_status(10, {
            "wallet": True,
            "skills": True,
            "orders": False,
            "location": False,
        })

        # 1 INSERT ON CONFLICT DO NOTHING + 1 UPDATE
        assert len(cur._executed) == 2

        insert_sql = cur._executed[0][0]
        assert "INSERT INTO character_sync_status" in insert_sql
        assert "ON CONFLICT" in insert_sql
        assert "DO NOTHING" in insert_sql

        update_sql = cur._executed[1][0]
        assert "wallets_synced_at = NOW()" in update_sql
        assert "skills_synced_at = NOW()" in update_sql
        assert "orders_synced_at" not in update_sql
        assert "location_synced_at" not in update_sql

    def test_always_includes_updated_at(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.update_sync_status(10, {"wallet": True})

        update_sql = cur._executed[1][0]
        assert "updated_at = NOW()" in update_sql

    def test_all_false_still_updates_updated_at(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.update_sync_status(10, {
            "wallet": False,
            "skills": False,
        })

        # Even with no successful syncs, updated_at is set
        assert len(cur._executed) == 2
        update_sql = cur._executed[1][0]
        assert "updated_at = NOW()" in update_sql
        assert "wallets_synced_at" not in update_sql

    def test_all_sync_types(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.update_sync_status(10, {
            "wallet": True, "skills": True, "skillqueue": True,
            "orders": True, "jobs": True, "blueprints": True,
            "assets": True, "location": True, "ship": True,
        })

        update_sql = cur._executed[1][0]
        assert "wallets_synced_at = NOW()" in update_sql
        assert "skills_synced_at = NOW()" in update_sql
        assert "skill_queue_synced_at = NOW()" in update_sql
        assert "orders_synced_at = NOW()" in update_sql
        assert "industry_jobs_synced_at = NOW()" in update_sql
        assert "blueprints_synced_at = NOW()" in update_sql
        assert "assets_synced_at = NOW()" in update_sql
        assert "location_synced_at = NOW()" in update_sql
        assert "ship_synced_at = NOW()" in update_sql

    def test_character_id_in_both_queries(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.update_sync_status(42, {"wallet": True})

        assert cur._executed[0][1] == (42,)
        assert cur._executed[1][1] == (42,)

    def test_empty_results_dict(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.update_sync_status(10, {})

        # INSERT + UPDATE (only updated_at)
        assert len(cur._executed) == 2
        update_sql = cur._executed[1][0]
        assert "updated_at = NOW()" in update_sql


# ---------------------------------------------------------------------------
# _batch_resolve_type_names
# ---------------------------------------------------------------------------

class TestBatchResolveTypeNames:
    def test_returns_dict(self):
        cur = MockCursor([
            {"typeID": 34, "typeName": "Tritanium"},
            {"typeID": 35, "typeName": "Pyerite"},
        ])
        repo = _make_repo(cur)
        result = repo._batch_resolve_type_names(cur, [34, 35])

        assert result == {34: "Tritanium", 35: "Pyerite"}

    def test_empty_input_returns_empty_dict(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        result = repo._batch_resolve_type_names(cur, [])

        assert result == {}
        assert len(cur._executed) == 0  # no query issued

    def test_query_uses_any(self):
        cur = MockCursor([])
        repo = _make_repo(cur)
        repo._batch_resolve_type_names(cur, [100, 200])

        sql = cur.last_sql
        assert '"invTypes"' in sql
        assert "ANY(%s)" in sql
        assert cur.last_params == ([100, 200],)


# ---------------------------------------------------------------------------
# _batch_resolve_station_names
# ---------------------------------------------------------------------------

class TestBatchResolveStationNames:
    def test_returns_dict(self):
        cur = MockCursor([
            {"stationID": 60003760, "stationName": "Jita IV - Moon 4 - Caldari Navy Assembly Plant"},
        ])
        repo = _make_repo(cur)
        result = repo._batch_resolve_station_names(cur, [60003760])

        assert result == {60003760: "Jita IV - Moon 4 - Caldari Navy Assembly Plant"}

    def test_empty_input_returns_empty_dict(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        result = repo._batch_resolve_station_names(cur, [])

        assert result == {}
        assert len(cur._executed) == 0

    def test_query_uses_sta_stations(self):
        cur = MockCursor([])
        repo = _make_repo(cur)
        repo._batch_resolve_station_names(cur, [60003760])

        sql = cur.last_sql
        assert '"staStations"' in sql
        assert "ANY(%s)" in sql


# ---------------------------------------------------------------------------
# get_all_summaries_from_db
# ---------------------------------------------------------------------------

class TestGetAllSummariesFromDB:
    def test_returns_empty_for_no_characters(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        # Mock get_all_characters to return empty
        repo.get_all_characters = MagicMock(return_value=[])

        result = repo.get_all_summaries_from_db()
        assert result == []

    def test_returns_empty_for_filtered_no_match(self):
        cur = MockCursor()
        repo = _make_repo(cur)
        repo.get_all_characters = MagicMock(return_value=[
            {"character_id": 100, "character_name": "Pilot A"}
        ])

        result = repo.get_all_summaries_from_db(character_ids=[999])
        assert result == []

    def test_assembles_character_data(self):
        """Full integration test with 7 batch queries."""
        cid = 100
        wallet_row = {"character_id": cid, "balance": Decimal("1000000.50"), "recorded_at": datetime(2026, 1, 1)}
        skill_row = {"character_id": cid, "total_sp": 5000000, "skill_count": 100}
        queue_row = {"character_id": cid, "queue_position": 0, "skill_id": 3300,
                     "skill_name": "Gunnery", "finished_level": 5,
                     "start_date": datetime(2026, 1, 1), "finish_date": datetime(2026, 1, 2)}
        location_row = {"character_id": cid, "solar_system_id": 30000142,
                        "station_id": 60003760, "structure_id": None,
                        "solar_system_name": "Jita"}
        ship_row = {"character_id": cid, "ship_item_id": 123, "ship_type_id": 24698,
                    "ship_name": "My Drake", "ship_type_name": "Drake"}
        job_row = {"character_id": cid, "job_id": 1, "activity_id": 1,
                   "blueprint_type_name": "Drake BPC", "product_type_name": "Drake",
                   "status": "active", "start_date": datetime(2026, 1, 1),
                   "end_date": datetime(2026, 1, 2), "runs": 1}
        sync_row = {"character_id": cid, "updated_at": datetime(2026, 1, 1, 12, 0, 0),
                    "wallets_synced_at": datetime(2026, 1, 1)}

        multi_cur = MultiResultCursor([
            [wallet_row],    # 1. wallet query
            [skill_row],     # 2. skills query
            [queue_row],     # 3. skill queue query
            [location_row],  # 4. location query
            [ship_row],      # 5. ship query
            [job_row],       # 6. industry jobs query
            [sync_row],      # 7. sync status query
        ])
        repo = _make_repo(multi_cur)
        repo.get_all_characters = MagicMock(return_value=[
            {"character_id": cid, "character_name": "TestPilot"}
        ])

        result = repo.get_all_summaries_from_db()
        assert len(result) == 1

        char = result[0]
        assert char["character_id"] == cid
        assert char["character_name"] == "TestPilot"
        assert char["wallet"]["balance"] == 1000000.50
        assert char["skills"]["total_sp"] == 5000000
        assert char["skills"]["skill_count"] == 100
        assert len(char["skillqueue"]["queue"]) == 1
        assert char["location"]["solar_system_name"] == "Jita"
        assert char["ship"]["ship_type_name"] == "Drake"
        assert char["industry"]["active_jobs"] == 1
        assert char["last_synced"] is not None

    def test_missing_data_returns_none_fields(self):
        """Character with no wallet/skills/etc data should have None fields."""
        cid = 200
        multi_cur = MultiResultCursor([
            [],  # no wallet
            [],  # no skills
            [],  # no queue
            [],  # no location
            [],  # no ship
            [],  # no jobs
            [],  # no sync status
        ])
        repo = _make_repo(multi_cur)
        repo.get_all_characters = MagicMock(return_value=[
            {"character_id": cid, "character_name": "EmptyPilot"}
        ])

        result = repo.get_all_summaries_from_db()
        assert len(result) == 1

        char = result[0]
        assert char["wallet"] is None
        assert char["skills"] is None
        assert char["skillqueue"] is None
        assert char["location"] is None
        assert char["ship"] is None
        assert char["industry"] is None
        assert char["last_synced"] is None

    def test_executes_7_queries(self):
        """Should issue exactly 7 SQL queries for the batch reads."""
        cid = 300
        multi_cur = MultiResultCursor([[], [], [], [], [], [], []])
        repo = _make_repo(multi_cur)
        repo.get_all_characters = MagicMock(return_value=[
            {"character_id": cid, "character_name": "P"}
        ])

        repo.get_all_summaries_from_db()
        assert len(multi_cur._executed) == 7
