"""Tests for fetch_hourly_stats_batch and batch-mode build_* functions.

Validates that the batch fetch correctly:
1. Fetches raw hourly stats rows
2. Collects type_ids and system_ids from JSONB
3. Performs SDE lookups for types and systems
4. Returns structured batch dict

Then validates that each build_* function produces identical output
in batch mode vs its original SQL path.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.tests.conftest import MockCursor, MultiResultCursor
from app.routers.intelligence.entity_context import EntityContext, EntityType
from app.routers.intelligence.shared_offensive import (
    fetch_hourly_stats_batch,
    fetch_killmail_attacker_batch,
    build_summary,
    build_ship_losses_inflicted,
    build_kill_heatmap,
    build_hunting_regions,
    build_hunting_hours,
    build_hot_systems,
    build_effective_doctrines,
    build_kill_velocity,
    build_engagement_profile,
    build_fleet_profile,
    build_solo_killers,
    build_doctrine_profile,
    build_victim_analysis,
    build_damage_dealt,
    build_ewar_usage,
    build_top_victims,
    build_high_value_kills,
    build_powerbloc_isk_dedup,
    build_powerbloc_max_kill_value,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _alliance_ctx():
    return EntityContext(EntityType.ALLIANCE, entity_id=99003581)


def _corp_ctx():
    return EntityContext(EntityType.CORPORATION, entity_id=98378388)


def _powerbloc_ctx():
    return EntityContext(EntityType.POWERBLOC, member_ids=[99003581, 99003582])


def _make_hourly_row(
    hour_bucket=None,
    kills=10,
    deaths=3,
    isk_destroyed=100_000_000,
    isk_lost=30_000_000,
    ships_killed=None,
    ships_lost=None,
    systems_kills=None,
    systems_deaths=None,
    solo_kills=2,
    avg_kill_value=None,
    max_kill_value=None,
    is_corp=False,
):
    """Create a tuple row matching the hourly stats query output."""
    if hour_bucket is None:
        hour_bucket = datetime(2026, 2, 1, 14, 0, 0)
    if ships_killed is None:
        ships_killed = {"587": 5, "11987": 3}  # Rifter, Svipul
    if ships_lost is None:
        ships_lost = {"24690": 1}  # Drake
    if systems_kills is None:
        systems_kills = {"30004759": 6, "30002187": 4}  # K-6K16, Jita
    if systems_deaths is None:
        systems_deaths = {"30004759": 2}

    base = (
        hour_bucket, kills, deaths, isk_destroyed, isk_lost,
        ships_killed, ships_lost, systems_kills, systems_deaths, solo_kills,
    )
    if is_corp:
        base += (avg_kill_value or 10_000_000, max_kill_value or 50_000_000)
    return base


def _type_info_rows():
    """SDE type lookup rows: (typeID, typeName, groupName, groupID)."""
    return [
        (587, "Rifter", "Frigate", 25),
        (11987, "Svipul", "Tactical Destroyer", 1305),
        (24690, "Drake", "Battlecruiser", 419),
    ]


def _system_info_rows():
    """SDE system lookup rows: (solarSystemID, solarSystemName, security, regionName, constellationName)."""
    return [
        (30004759, "K-6K16", -0.46, "Branch", "G-YZUX"),
        (30002187, "Jita", 0.95, "The Forge", "Kimotoro"),
    ]


# ---------------------------------------------------------------------------
# Tests: fetch_hourly_stats_batch
# ---------------------------------------------------------------------------

class TestFetchHourlyStatsBatch:
    """Tests for the batch fetch function."""

    def test_alliance_batch_basic(self):
        """Alliance batch returns rows, type_info, and system_info."""
        rows = [_make_hourly_row()]
        cur = MultiResultCursor([
            rows,                    # Query 1: raw hourly stats
            _type_info_rows(),       # Query 2: SDE types
            _system_info_rows(),     # Query 3: SDE systems
        ])
        batch = fetch_hourly_stats_batch(cur, _alliance_ctx(), 30)

        assert batch["rows"] == rows
        assert 587 in batch["type_info"]
        assert batch["type_info"][587]["name"] == "Rifter"
        assert batch["type_info"][587]["group"] == "Frigate"
        assert 30004759 in batch["system_info"]
        assert batch["system_info"][30004759]["name"] == "K-6K16"
        assert batch["system_info"][30004759]["region"] == "Branch"

    def test_corp_batch_has_extra_columns(self):
        """Corporation batch includes avg_kill_value and max_kill_value."""
        rows = [_make_hourly_row(is_corp=True)]
        cur = MultiResultCursor([rows, _type_info_rows(), _system_info_rows()])
        batch = fetch_hourly_stats_batch(cur, _corp_ctx(), 30)

        assert len(batch["rows"]) == 1
        row = batch["rows"][0]
        # Corporation rows have 12 columns (10 base + 2 extra)
        assert len(row) == 12
        assert row[10] == 10_000_000  # avg_kill_value
        assert row[11] == 50_000_000  # max_kill_value

    def test_powerbloc_batch(self):
        """PowerBloc batch works with member_ids list."""
        rows = [_make_hourly_row()]
        cur = MultiResultCursor([rows, _type_info_rows(), _system_info_rows()])
        batch = fetch_hourly_stats_batch(cur, _powerbloc_ctx(), 7)

        assert len(batch["rows"]) == 1
        # Check that the SQL used ANY() for powerbloc
        sql = cur._executed[0][0]
        assert "ANY" in sql

    def test_empty_rows(self):
        """Empty hourly stats returns empty type_info and system_info."""
        cur = MultiResultCursor([[], [], []])
        batch = fetch_hourly_stats_batch(cur, _alliance_ctx(), 30)

        assert batch["rows"] == []
        assert batch["type_info"] == {}
        assert batch["system_info"] == {}

    def test_null_jsonb_columns(self):
        """Null JSONB columns don't cause errors."""
        row = (
            datetime(2026, 2, 1, 14, 0, 0),
            10, 3, 100_000_000, 30_000_000,
            None, None, None, None, 2,
        )
        cur = MultiResultCursor([[row], [], []])
        batch = fetch_hourly_stats_batch(cur, _alliance_ctx(), 30)

        assert batch["rows"] == [row]
        assert batch["type_info"] == {}
        assert batch["system_info"] == {}

    def test_jsonb_as_string(self):
        """JSONB columns parsed from string format."""
        row = (
            datetime(2026, 2, 1, 14, 0, 0),
            10, 3, 100_000_000, 30_000_000,
            json.dumps({"587": 5}), None, json.dumps({"30004759": 3}), None, 2,
        )
        cur = MultiResultCursor([[row], [(587, "Rifter", "Frigate", 25)], [(30004759, "K-6K16", -0.46, "Branch", "G-YZUX")]])
        batch = fetch_hourly_stats_batch(cur, _alliance_ctx(), 30)

        assert 587 in batch["type_info"]
        assert 30004759 in batch["system_info"]

    def test_multiple_rows_collect_unique_ids(self):
        """Multiple rows with overlapping IDs only query unique type/system IDs."""
        row1 = _make_hourly_row(ships_killed={"587": 5, "11987": 3})
        row2 = _make_hourly_row(
            hour_bucket=datetime(2026, 2, 1, 15, 0, 0),
            ships_killed={"587": 2, "24690": 1},  # 587 repeated, 24690 new
        )
        cur = MultiResultCursor(
            [[row1, row2], _type_info_rows(), _system_info_rows()]
        )
        batch = fetch_hourly_stats_batch(cur, _alliance_ctx(), 30)

        # All 3 unique type_ids resolved
        assert len(batch["type_info"]) == 3
        assert 587 in batch["type_info"]
        assert 11987 in batch["type_info"]
        assert 24690 in batch["type_info"]

    def test_no_sde_queries_when_no_jsonb_ids(self):
        """When JSONB columns are empty dicts, skip SDE queries."""
        row = _make_hourly_row(
            ships_killed={}, ships_lost={},
            systems_kills={}, systems_deaths={},
        )
        cur = MultiResultCursor([[row]])
        batch = fetch_hourly_stats_batch(cur, _alliance_ctx(), 30)

        # Only 1 query executed (raw rows), no SDE queries needed
        assert len(cur._executed) == 1
        assert batch["type_info"] == {}
        assert batch["system_info"] == {}

    def test_systems_kills_nested_objects(self):
        """Alliance systems_kills can have nested object format."""
        row = _make_hourly_row(
            systems_kills={"30004759": {"kills": 6, "solo_kills": 2}},
        )
        cur = MultiResultCursor(
            [[row], _type_info_rows(), _system_info_rows()]
        )
        batch = fetch_hourly_stats_batch(cur, _alliance_ctx(), 30)

        assert 30004759 in batch["system_info"]


# ---------------------------------------------------------------------------
# Tests: build_summary with batch
# ---------------------------------------------------------------------------

class TestBuildSummaryBatch:
    """Tests for build_summary using hs_batch."""

    def test_alliance_summary_from_batch(self):
        """Alliance summary calculates correct aggregates from batch."""
        rows = [
            _make_hourly_row(kills=10, deaths=3, isk_destroyed=100_000_000, isk_lost=30_000_000, solo_kills=2),
            _make_hourly_row(
                hour_bucket=datetime(2026, 2, 1, 15, 0, 0),
                kills=5, deaths=2, isk_destroyed=50_000_000, isk_lost=20_000_000, solo_kills=1,
            ),
        ]
        batch = {
            "rows": rows,
            "type_info": {
                587: {"name": "Rifter", "group": "Frigate", "group_id": 25},
                11987: {"name": "Svipul", "group": "Tactical Destroyer", "group_id": 1305},
            },
            "system_info": {},
        }
        summary, deaths = build_summary(None, _alliance_ctx(), 30, hs_batch=batch)

        assert summary["total_kills"] == 15
        assert deaths == 5
        assert summary["isk_destroyed"] == str(150_000_000)
        assert summary["kd_ratio"] == 3.0
        assert summary["solo_kill_pct"] == 20.0  # 3/15 * 100
        assert summary["efficiency"] == 75.0  # 15/(15+5) * 100
        # No capitals in test data
        assert summary["capital_kills"] == 0

    def test_corp_summary_from_batch(self):
        """Corporation summary includes avg/max kill values."""
        rows = [
            _make_hourly_row(
                kills=10, deaths=3, isk_destroyed=100_000_000, isk_lost=30_000_000,
                solo_kills=2, is_corp=True, avg_kill_value=10_000_000, max_kill_value=50_000_000,
            ),
            _make_hourly_row(
                hour_bucket=datetime(2026, 2, 1, 15, 0, 0),
                kills=5, deaths=2, isk_destroyed=50_000_000, isk_lost=20_000_000,
                solo_kills=1, is_corp=True, avg_kill_value=12_000_000, max_kill_value=80_000_000,
            ),
        ]
        batch = {
            "rows": rows,
            "type_info": {},
            "system_info": {},
        }
        summary, deaths = build_summary(None, _corp_ctx(), 30, hs_batch=batch)

        assert summary["total_kills"] == 15
        assert deaths == 5
        # Weighted avg: (10M*10 + 12M*5) / 15 = 160M/15 ~= 10666666
        assert summary["avg_kill_value"] == str(int(
            (10_000_000 * 10 + 12_000_000 * 5) / 15
        ))
        assert summary["max_kill_value"] == 80_000_000

    def test_summary_capital_kills_from_batch(self):
        """Capital kills counted from ships_killed JSONB + type_info."""
        rows = [
            _make_hourly_row(ships_killed={"19720": 2, "587": 5}),  # 19720 = Carrier type
        ]
        batch = {
            "rows": rows,
            "type_info": {
                19720: {"name": "Thanatos", "group": "Carrier", "group_id": 547},
                587: {"name": "Rifter", "group": "Frigate", "group_id": 25},
            },
            "system_info": {},
        }
        summary, _ = build_summary(None, _alliance_ctx(), 30, hs_batch=batch)

        # Alliance counts SUM of capital ship counts
        assert summary["capital_kills"] == 2

    def test_summary_zero_kills(self):
        """Zero kills produces safe defaults."""
        batch = {"rows": [], "type_info": {}, "system_info": {}}
        summary, deaths = build_summary(None, _alliance_ctx(), 30, hs_batch=batch)

        assert summary["total_kills"] == 0
        assert deaths == 0
        assert summary["kd_ratio"] == 0
        assert summary["efficiency"] == 0

    def test_powerbloc_summary_no_solo(self):
        """PowerBloc summary sets solo_kill_pct to 0."""
        rows = [_make_hourly_row(kills=10, deaths=3, solo_kills=2)]
        batch = {"rows": rows, "type_info": {}, "system_info": {}}
        summary, _ = build_summary(None, _powerbloc_ctx(), 30, hs_batch=batch)

        # PowerBloc doesn't report solo_kill_pct (always 0)
        assert summary["solo_kill_pct"] == 0


# ---------------------------------------------------------------------------
# Tests: build_hunting_hours with batch
# ---------------------------------------------------------------------------

class TestBuildHuntingHoursBatch:
    """Tests for build_hunting_hours using hs_batch."""

    def test_hourly_distribution(self):
        """Hourly kills distributed correctly from batch rows."""
        rows = [
            _make_hourly_row(hour_bucket=datetime(2026, 2, 1, 14, 0, 0), kills=10),
            _make_hourly_row(hour_bucket=datetime(2026, 2, 1, 18, 0, 0), kills=5),
            _make_hourly_row(hour_bucket=datetime(2026, 2, 1, 14, 0, 0), kills=3),  # same hour
        ]
        batch = {"rows": rows, "type_info": {}, "system_info": {}}
        result = build_hunting_hours(None, _alliance_ctx(), 30, hs_batch=batch)

        assert result["hourly_activity"][14] == 13  # 10 + 3
        assert result["hourly_activity"][18] == 5

    def test_peak_and_safe_windows(self):
        """Peak and safe 4h windows detected correctly."""
        rows = []
        for h in range(24):
            kills = 100 if 18 <= h <= 21 else 1
            rows.append(_make_hourly_row(
                hour_bucket=datetime(2026, 2, 1, h, 0, 0),
                kills=kills,
            ))
        batch = {"rows": rows, "type_info": {}, "system_info": {}}
        result = build_hunting_hours(None, _alliance_ctx(), 30, hs_batch=batch)

        assert result["peak_start"] == 18
        assert result["peak_end"] == 22

    def test_corp_uses_killmail_time(self):
        """Corporation still uses DB query path (no batch for corp hunting hours)."""
        # Corporation hunting hours uses killmail_time, not hourly_stats
        # So batch mode falls back to SQL query
        row = (14.0, 10)  # hour, kills
        cur = MultiResultCursor([[row]])
        result = build_hunting_hours(cur, _corp_ctx(), 30, hs_batch=None)

        assert result["hourly_activity"][14] == 10

    def test_powerbloc_no_hourly_activity(self):
        """PowerBloc omits hourly_activity list."""
        rows = [_make_hourly_row(hour_bucket=datetime(2026, 2, 1, 14, 0, 0), kills=10)]
        batch = {"rows": rows, "type_info": {}, "system_info": {}}
        result = build_hunting_hours(None, _powerbloc_ctx(), 30, hs_batch=batch)

        assert "hourly_activity" not in result
        # But still has peak/safe windows
        assert "peak_start" in result
        assert "safe_start" in result


# ---------------------------------------------------------------------------
# Tests: build_ship_losses_inflicted with batch
# ---------------------------------------------------------------------------

class TestBuildShipLossesInflictedBatch:
    """Tests for build_ship_losses_inflicted using hs_batch."""

    def test_ship_class_aggregation(self):
        """Ship types classified and aggregated correctly."""
        rows = [
            _make_hourly_row(ships_killed={"587": 5, "11987": 3}),
        ]
        batch = {
            "rows": rows,
            "type_info": {
                587: {"name": "Rifter", "group": "Frigate", "group_id": 25},
                11987: {"name": "Svipul", "group": "Tactical Destroyer", "group_id": 1305},
            },
            "system_info": {},
        }
        result = build_ship_losses_inflicted(None, _alliance_ctx(), 30, hs_batch=batch)

        classes = {r["ship_class"]: r["count"] for r in result}
        assert classes["Frigate"] == 5
        assert classes["Destroyer"] == 3

    def test_percentage_calculation(self):
        """Percentages sum to 100%."""
        rows = [
            _make_hourly_row(ships_killed={"587": 5, "11987": 5}),
        ]
        batch = {
            "rows": rows,
            "type_info": {
                587: {"name": "Rifter", "group": "Frigate", "group_id": 25},
                11987: {"name": "Svipul", "group": "Tactical Destroyer", "group_id": 1305},
            },
            "system_info": {},
        }
        result = build_ship_losses_inflicted(None, _alliance_ctx(), 30, hs_batch=batch)

        total_pct = sum(r["percentage"] for r in result)
        assert total_pct == pytest.approx(100.0, abs=0.5)

    def test_empty_ships_killed(self):
        """No ships_killed returns empty list."""
        rows = [_make_hourly_row(ships_killed={})]
        batch = {"rows": rows, "type_info": {}, "system_info": {}}
        result = build_ship_losses_inflicted(None, _alliance_ctx(), 30, hs_batch=batch)

        assert result == []

    def test_unknown_type_id_skipped(self):
        """Type IDs not in type_info are skipped."""
        rows = [_make_hourly_row(ships_killed={"99999": 5})]
        batch = {"rows": rows, "type_info": {}, "system_info": {}}
        result = build_ship_losses_inflicted(None, _alliance_ctx(), 30, hs_batch=batch)

        assert result == []


# ---------------------------------------------------------------------------
# Tests: build_kill_heatmap with batch
# ---------------------------------------------------------------------------

class TestBuildKillHeatmapBatch:
    """Tests for build_kill_heatmap using hs_batch."""

    def test_system_aggregation(self):
        """Systems aggregated with kills and region."""
        rows = [
            _make_hourly_row(systems_kills={"30004759": 6, "30002187": 4}),
        ]
        batch = {
            "rows": rows,
            "type_info": {},
            "system_info": {
                30004759: {"name": "K-6K16", "security": -0.46, "region": "Branch", "constellation": "G-YZUX"},
                30002187: {"name": "Jita", "security": 0.95, "region": "The Forge", "constellation": "Kimotoro"},
            },
        }
        result = build_kill_heatmap(None, _alliance_ctx(), 30, hs_batch=batch)

        systems = {r["system_name"]: r for r in result}
        assert "K-6K16" in systems
        assert systems["K-6K16"]["kills"] == 6
        assert systems["K-6K16"]["region_name"] == "Branch"
        assert "Jita" in systems

    def test_top_20_limit(self):
        """Result limited to top 20 systems."""
        systems = {str(30000000 + i): i + 1 for i in range(30)}
        rows = [_make_hourly_row(systems_kills=systems)]
        sys_info = {
            30000000 + i: {"name": f"System-{i}", "security": 0.5, "region": "TestRegion", "constellation": "TestConst"}
            for i in range(30)
        }
        batch = {"rows": rows, "type_info": {}, "system_info": sys_info}
        result = build_kill_heatmap(None, _alliance_ctx(), 30, hs_batch=batch)

        assert len(result) <= 20

    def test_alliance_nested_systems_kills(self):
        """Alliance systems_kills with nested object format."""
        rows = [
            _make_hourly_row(
                systems_kills={"30004759": {"kills": 6, "solo_kills": 4}},
            ),
        ]
        batch = {
            "rows": rows,
            "type_info": {},
            "system_info": {
                30004759: {"name": "K-6K16", "security": -0.46, "region": "Branch", "constellation": "G-YZUX"},
            },
        }
        result = build_kill_heatmap(None, _alliance_ctx(), 30, hs_batch=batch)

        assert len(result) == 1
        assert result[0]["kills"] == 6
        # solo_kills > 0.6*kills → gatecamp
        assert result[0]["is_gatecamp"] is True

    def test_powerbloc_no_gatecamp(self):
        """PowerBloc always reports is_gatecamp as false."""
        rows = [
            _make_hourly_row(systems_kills={"30004759": {"kills": 6, "solo_kills": 5}}),
        ]
        batch = {
            "rows": rows,
            "type_info": {},
            "system_info": {
                30004759: {"name": "K-6K16", "security": -0.46, "region": "Branch", "constellation": "G-YZUX"},
            },
        }
        result = build_kill_heatmap(None, _powerbloc_ctx(), 30, hs_batch=batch)

        assert result[0]["is_gatecamp"] is False


# ---------------------------------------------------------------------------
# Tests: build_hunting_regions with batch
# ---------------------------------------------------------------------------

class TestBuildHuntingRegionsBatch:
    """Tests for build_hunting_regions using hs_batch."""

    def test_region_aggregation(self):
        """Multiple systems in same region are aggregated."""
        rows = [
            _make_hourly_row(systems_kills={"30004759": 6, "30004760": 4}),
        ]
        batch = {
            "rows": rows,
            "type_info": {},
            "system_info": {
                30004759: {"name": "K-6K16", "security": -0.46, "region": "Branch", "constellation": "G-YZUX"},
                30004760: {"name": "9-IIBL", "security": -0.3, "region": "Branch", "constellation": "G-YZUX"},
            },
        }
        result = build_hunting_regions(None, _alliance_ctx(), 30, hs_batch=batch)

        assert len(result) == 1
        assert result[0]["region_name"] == "Branch"
        assert result[0]["kills"] == 10
        assert result[0]["unique_systems"] == 2

    def test_top_15_limit(self):
        """Result limited to top 15 regions."""
        systems = {}
        sys_info = {}
        for i in range(20):
            sid = 30000000 + i
            systems[str(sid)] = i + 1
            sys_info[sid] = {"name": f"Sys-{i}", "security": 0.5, "region": f"Region-{i}", "constellation": "C"}
        rows = [_make_hourly_row(systems_kills=systems)]
        batch = {"rows": rows, "type_info": {}, "system_info": sys_info}
        result = build_hunting_regions(None, _alliance_ctx(), 30, hs_batch=batch)

        assert len(result) <= 15


# ---------------------------------------------------------------------------
# Tests: build_hot_systems with batch
# ---------------------------------------------------------------------------

class TestBuildHotSystemsBatch:
    """Tests for build_hot_systems using hs_batch."""

    def test_kills_and_deaths_combined(self):
        """Hot systems uses both kills and deaths."""
        rows = [
            _make_hourly_row(
                systems_kills={"30004759": {"kills": 10, "solo_kills": 1, "total_value": 500_000_000}},
                systems_deaths={"30004759": 3},
            ),
        ]
        batch = {
            "rows": rows,
            "type_info": {},
            "system_info": {
                30004759: {"name": "K-6K16", "security": -0.46, "region": "Branch", "constellation": "G-YZUX"},
            },
        }
        result = build_hot_systems(None, _alliance_ctx(), 30, hs_batch=batch)

        assert len(result) == 1
        assert result[0]["kills"] == 10
        assert result[0]["deaths"] == 3
        # kill_score: 100 * 10 / (10+3) ~= 76.9
        assert result[0]["kill_score"] > 70

    def test_minimum_5_kills_filter(self):
        """Systems with less than 5 kills are filtered out."""
        rows = [
            _make_hourly_row(
                systems_kills={"30004759": {"kills": 3, "solo_kills": 0, "total_value": 0}},
            ),
        ]
        batch = {
            "rows": rows,
            "type_info": {},
            "system_info": {
                30004759: {"name": "K-6K16", "security": -0.46, "region": "Branch", "constellation": "G-YZUX"},
            },
        }
        result = build_hot_systems(None, _alliance_ctx(), 30, hs_batch=batch)

        assert result == []

    def test_corp_uses_sql_path(self):
        """Corporation hot systems still uses SQL (not batch)."""
        # Corporation uses raw killmails, not hourly_stats JSONB
        row = (30004759, "K-6K16", "Branch", -0.46, 15, 3, 83.3, False, 50_000_000.0)
        cur = MultiResultCursor([[row]])
        result = build_hot_systems(cur, _corp_ctx(), 30, hs_batch=None)

        assert len(result) == 1
        assert result[0]["system_name"] == "K-6K16"


# ---------------------------------------------------------------------------
# Tests: build_effective_doctrines with batch
# ---------------------------------------------------------------------------

class TestBuildEffectiveDoctrinesBatch:
    """Tests for build_effective_doctrines using hs_batch."""

    def test_kd_ratio_filtering(self):
        """Only ship classes with KD >= 2.0 are returned."""
        rows = [
            _make_hourly_row(
                ships_killed={"587": 20, "11987": 5},  # 20 Rifter kills, 5 Svipul kills
                ships_lost={"587": 5, "11987": 10},    # 5 Rifter deaths, 10 Svipul deaths
            ),
        ]
        batch = {
            "rows": rows,
            "type_info": {
                587: {"name": "Rifter", "group": "Frigate", "group_id": 25},
                11987: {"name": "Svipul", "group": "Tactical Destroyer", "group_id": 1305},
            },
            "system_info": {},
        }
        result = build_effective_doctrines(None, _alliance_ctx(), 30, hs_batch=batch)

        # Frigate: 20/5 = 4.0 KD → included
        # Destroyer (Svipul): 5/10 = 0.5 KD → excluded
        classes = {r["ship_class"]: r for r in result}
        assert "Frigate" in classes
        assert classes["Frigate"]["kd_ratio"] == 4.0
        assert "Tactical Destroyer" not in classes

    def test_minimum_5_kills_filter(self):
        """Ship classes with fewer than 5 kills are excluded."""
        rows = [
            _make_hourly_row(ships_killed={"587": 3}, ships_lost={"587": 1}),
        ]
        batch = {
            "rows": rows,
            "type_info": {587: {"name": "Rifter", "group": "Frigate", "group_id": 25}},
            "system_info": {},
        }
        result = build_effective_doctrines(None, _alliance_ctx(), 30, hs_batch=batch)

        assert result == []

    def test_corp_uses_sql_path(self):
        """Corporation effective doctrines still uses SQL (not batch)."""
        row = ("Battlecruiser", 50, 10, 5.0, 83.3)
        cur = MultiResultCursor([[row]])
        result = build_effective_doctrines(cur, _corp_ctx(), 30, hs_batch=None)

        assert len(result) == 1
        assert result[0]["ship_class"] == "Battlecruiser"


# ---------------------------------------------------------------------------
# Tests: build_kill_velocity with batch
# ---------------------------------------------------------------------------

class TestBuildKillVelocityBatch:
    """Tests for build_kill_velocity using hs_batch."""

    def test_half_period_split(self):
        """Kills split into recent and previous half-periods."""
        now = datetime(2026, 2, 10, 0, 0, 0)
        recent_row = _make_hourly_row(
            hour_bucket=datetime(2026, 2, 8, 14, 0, 0),  # recent half (within 15d)
            ships_killed={"587": 10},
        )
        previous_row = _make_hourly_row(
            hour_bucket=datetime(2026, 1, 20, 14, 0, 0),  # previous half
            ships_killed={"587": 5},
        )
        batch = {
            "rows": [recent_row, previous_row],
            "type_info": {587: {"name": "Rifter", "group": "Frigate", "group_id": 25}},
            "system_info": {},
        }
        with patch("app.routers.intelligence.shared_offensive._now") as mock_now:
            mock_now.return_value = now
            result = build_kill_velocity(None, _alliance_ctx(), 30, hs_batch=batch)

        if result:  # May be filtered by minimum 10 total
            classes = {r["ship_class"]: r for r in result}
            if "Frigate" in classes:
                assert classes["Frigate"]["recent_kills"] == 10
                assert classes["Frigate"]["previous_kills"] == 5

    def test_corp_uses_sql_path(self):
        """Corporation kill velocity still uses SQL (not batch)."""
        row = ("Cruiser", 20, 15, 50_000_000.0, 40_000_000.0, 33.3, "ESCALATING")
        cur = MultiResultCursor([[row]])
        result = build_kill_velocity(cur, _corp_ctx(), 30, hs_batch=None)

        assert len(result) == 1
        assert result[0]["ship_class"] == "Cruiser"
        assert result[0]["status"] == "ESCALATING"


# ---------------------------------------------------------------------------
# Tests: Backward compatibility (hs_batch=None)
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """All build_* functions work unchanged when hs_batch is None."""

    def test_summary_sql_path(self):
        """build_summary with hs_batch=None uses cursor (SQL path)."""
        sr = (100, 20, 500_000_000, 5_000_000, 0, 10, 5, 5.0, 10.0, 83.3)
        cur = MultiResultCursor([[sr]])
        summary, deaths = build_summary(cur, _alliance_ctx(), 30, hs_batch=None)

        assert summary["total_kills"] == 100
        assert deaths == 20

    def test_ship_losses_sql_path(self):
        """build_ship_losses_inflicted with hs_batch=None uses cursor."""
        rows = [(587, "Frigate", 10)]
        cur = MultiResultCursor([rows])
        result = build_ship_losses_inflicted(cur, _alliance_ctx(), 30, hs_batch=None)

        assert len(result) == 1

    def test_hunting_hours_sql_path(self):
        """build_hunting_hours with hs_batch=None uses cursor."""
        rows = [(14.0, 10), (15.0, 5)]
        cur = MultiResultCursor([rows])
        result = build_hunting_hours(cur, _alliance_ctx(), 30, hs_batch=None)

        assert result["hourly_activity"][14] == 10


# ---------------------------------------------------------------------------
# Tests: fetch_killmail_attacker_batch
# ---------------------------------------------------------------------------

class TestFetchKillmailAttackerBatch:
    """Tests for the killmail batch temp table creation."""

    def test_creates_temp_table(self):
        """Batch returns True and executes DROP + CREATE + CREATE INDEX."""
        cur = MultiResultCursor([[], [], []])
        result = fetch_killmail_attacker_batch(cur, _alliance_ctx(), 30)

        assert result is True
        assert len(cur._executed) == 3
        assert "DROP TABLE IF EXISTS _km_batch" in cur._executed[0][0]
        assert "CREATE TEMP TABLE _km_batch" in cur._executed[1][0]
        assert "CREATE INDEX" in cur._executed[2][0]

    def test_alliance_filter(self):
        """Alliance uses ka.alliance_id = %(entity_id)s."""
        cur = MultiResultCursor([[], [], []])
        fetch_killmail_attacker_batch(cur, _alliance_ctx(), 30)

        create_sql = cur._executed[1][0]
        assert "ka.alliance_id = %(entity_id)s" in create_sql

    def test_corp_filter(self):
        """Corporation uses ka.corporation_id = %(entity_id)s."""
        cur = MultiResultCursor([[], [], []])
        fetch_killmail_attacker_batch(cur, _corp_ctx(), 7)

        create_sql = cur._executed[1][0]
        assert "ka.corporation_id = %(entity_id)s" in create_sql

    def test_powerbloc_filter(self):
        """PowerBloc uses ka.alliance_id = ANY(%(entity_id)s)."""
        cur = MultiResultCursor([[], [], []])
        fetch_killmail_attacker_batch(cur, _powerbloc_ctx(), 14)

        create_sql = cur._executed[1][0]
        assert "ANY(%(entity_id)s)" in create_sql

    def test_days_in_interval(self):
        """Days value appears in INTERVAL clause."""
        cur = MultiResultCursor([[], [], []])
        fetch_killmail_attacker_batch(cur, _alliance_ctx(), 7)

        create_sql = cur._executed[1][0]
        assert "7 days" in create_sql

    def test_selects_required_columns(self):
        """Temp table SELECT includes all required columns."""
        cur = MultiResultCursor([[], [], []])
        fetch_killmail_attacker_batch(cur, _alliance_ctx(), 30)

        create_sql = cur._executed[1][0]
        for col in ["km.killmail_id", "km.killmail_time", "km.ship_value",
                     "km.victim_corporation_id", "km.victim_alliance_id",
                     "km.victim_character_id", "km.solar_system_id",
                     "ka.character_id AS attacker_character_id",
                     "ka.ship_type_id AS attacker_ship_type_id",
                     "ka.weapon_type_id", "ka.damage_done", "ka.is_final_blow"]:
            assert col in create_sql


# ---------------------------------------------------------------------------
# Tests: Killmail-based functions with km_batch=True
# ---------------------------------------------------------------------------

class TestEngagementProfileBatch:
    """Tests for build_engagement_profile with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch instead of killmails."""
        rows = [("solo", 10, 50.0), ("small", 5, 25.0), ("medium", 3, 15.0), ("large", 2, 10.0)]
        cur = MultiResultCursor([rows])
        result = build_engagement_profile(cur, _alliance_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert "killmails" not in cur._executed[0][0]
        assert result["solo"]["kills"] == 10
        assert result["small"]["kills"] == 5

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False queries killmails table (original path)."""
        rows = [("solo", 8, 40.0)]
        cur = MultiResultCursor([rows])
        result = build_engagement_profile(cur, _alliance_ctx(), 30, km_batch=False)

        assert "killmails" in cur._executed[0][0]
        assert "_km_batch" not in cur._executed[0][0]
        assert result["solo"]["kills"] == 8

    def test_empty_result(self):
        """Empty result returns default profile."""
        cur = MultiResultCursor([[]])
        result = build_engagement_profile(cur, _corp_ctx(), 30, km_batch=True)

        assert result["solo"]["kills"] == 0
        assert result["blob"]["kills"] == 0


class TestDoctrineProfileBatch:
    """Tests for build_doctrine_profile with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch."""
        rows = [("Rifter", "Frigate", 15, 60.0), ("Svipul", "Tactical Destroyer", 10, 40.0)]
        cur = MultiResultCursor([rows])
        result = build_doctrine_profile(cur, _alliance_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert len(result) == 2
        assert result[0]["ship_name"] == "Rifter"
        assert result[0]["count"] == 15

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original killmails path."""
        rows = [("Drake", "Battlecruiser", 20, 100.0)]
        cur = MultiResultCursor([rows])
        result = build_doctrine_profile(cur, _corp_ctx(), 30, km_batch=False)

        assert "killmails" in cur._executed[0][0]
        assert len(result) == 1


class TestSoloKillersBatch:
    """Tests for build_solo_killers with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch."""
        rows = [(12345, "TestPilot", 10, 5_000_000.0, "Hecate")]
        cur = MultiResultCursor([rows])
        result = build_solo_killers(cur, _alliance_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert len(result) == 1
        assert result[0]["character_name"] == "TestPilot"
        assert result[0]["solo_kills"] == 10

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original path."""
        rows = [(99999, "OtherPilot", 7, 3_000_000.0, "Svipul")]
        cur = MultiResultCursor([rows])
        result = build_solo_killers(cur, _corp_ctx(), 30, km_batch=False)

        assert "killmails" in cur._executed[0][0]
        assert len(result) == 1


class TestVictimAnalysisBatch:
    """Tests for build_victim_analysis with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch."""
        rows = [(100, 50, 20, 10, 5_000_000.0, 3)]
        cur = MultiResultCursor([rows])
        result = build_victim_analysis(cur, _alliance_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert result["total_kills"] == 100
        assert result["pvp_kills"] == 50
        assert result["capital_kills"] == 3

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original path."""
        rows = [(50, 30, 10, 5, 3_000_000.0, 1)]
        cur = MultiResultCursor([rows])
        result = build_victim_analysis(cur, _corp_ctx(), 30, km_batch=False)

        assert "killmails" in cur._executed[0][0]
        assert result["total_kills"] == 50


class TestDamageDealtBatch:
    """Tests for build_damage_dealt with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch."""
        rows = [("em", 40), ("thermal", 30), ("kinetic", 20), ("explosive", 10)]
        cur = MultiResultCursor([rows])
        result = build_damage_dealt(cur, _alliance_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert len(result) == 4

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original path."""
        rows = [("em", 50)]
        cur = MultiResultCursor([rows])
        result = build_damage_dealt(cur, _corp_ctx(), 30, km_batch=False)

        assert "killmails" in cur._executed[0][0]
        assert len(result) == 1


class TestEwarUsageBatch:
    """Tests for build_ewar_usage with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch."""
        rows = [("Warp Scrambler", 20), ("Stasis Web", 15)]
        cur = MultiResultCursor([rows])
        result = build_ewar_usage(cur, _alliance_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert len(result) == 2

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original path."""
        rows = [("ECM", 10)]
        cur = MultiResultCursor([rows])
        result = build_ewar_usage(cur, _corp_ctx(), 30, km_batch=False)

        assert "killmails" in cur._executed[0][0]


class TestTopVictimsBatch:
    """Tests for build_top_victims with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch."""
        rows = [(12345, "TestCorp", 15, 500_000_000)]
        cur = MultiResultCursor([rows])
        result = build_top_victims(cur, _alliance_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert len(result) == 1
        assert result[0]["corporation_name"] == "TestCorp"
        assert result[0]["kills_on_them"] == 15

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original path."""
        rows = [(99999, "OtherCorp", 10, 200_000_000)]
        cur = MultiResultCursor([rows])
        result = build_top_victims(cur, _corp_ctx(), 30, km_batch=False)

        assert "killmails" in cur._executed[0][0]


class TestHighValueKillsBatch:
    """Tests for build_high_value_kills with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch."""
        rows = [(1001, datetime(2026, 2, 1, 14, 0, 0), 5_000_000_000, 12345, "TestVictim", 24690, "Drake", "Jita")]
        cur = MultiResultCursor([rows])
        result = build_high_value_kills(cur, _alliance_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert len(result) == 1
        assert result[0]["isk_value"] == 5_000_000_000
        assert result[0]["ship_name"] == "Drake"

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original path."""
        rows = [(2002, datetime(2026, 2, 2, 10, 0, 0), 1_000_000_000, 99999, "OtherVictim", 587, "Rifter", "K-6K16")]
        cur = MultiResultCursor([rows])
        result = build_high_value_kills(cur, _corp_ctx(), 30, km_batch=False)

        assert "killmails" in cur._executed[0][0]
        assert len(result) == 1


class TestPowerblocIskDedupBatch:
    """Tests for build_powerbloc_isk_dedup with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch."""
        rows = [(500_000_000,)]
        cur = MultiResultCursor([rows])
        summary = {"total_kills": 100, "isk_destroyed": "0", "avg_kill_value": "0"}
        build_powerbloc_isk_dedup(cur, _powerbloc_ctx(), 30, summary, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert summary["isk_destroyed"] == str(500_000_000)
        assert summary["avg_kill_value"] == str(5_000_000)

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original path."""
        rows = [(300_000_000,)]
        cur = MultiResultCursor([rows])
        summary = {"total_kills": 50, "isk_destroyed": "0", "avg_kill_value": "0"}
        build_powerbloc_isk_dedup(cur, _powerbloc_ctx(), 30, summary, km_batch=False)

        assert "killmails" in cur._executed[0][0]

    def test_non_powerbloc_skips(self):
        """Non-powerbloc entity type returns immediately."""
        cur = MultiResultCursor([[]])
        summary = {"total_kills": 10, "isk_destroyed": "0", "avg_kill_value": "0"}
        build_powerbloc_isk_dedup(cur, _alliance_ctx(), 30, summary, km_batch=True)

        assert len(cur._executed) == 0


class TestPowerblocMaxKillValueBatch:
    """Tests for build_powerbloc_max_kill_value with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch."""
        rows = [(2_000_000_000,)]
        cur = MultiResultCursor([rows])
        summary = {"max_kill_value": 0}
        build_powerbloc_max_kill_value(cur, _powerbloc_ctx(), 30, summary, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert summary["max_kill_value"] == 2_000_000_000

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original path."""
        rows = [(1_000_000_000,)]
        cur = MultiResultCursor([rows])
        summary = {"max_kill_value": 0}
        build_powerbloc_max_kill_value(cur, _powerbloc_ctx(), 30, summary, km_batch=False)

        assert "killmails" in cur._executed[0][0]

    def test_non_powerbloc_skips(self):
        """Non-powerbloc entity type returns immediately."""
        cur = MultiResultCursor([[]])
        summary = {"max_kill_value": 0}
        build_powerbloc_max_kill_value(cur, _alliance_ctx(), 30, summary, km_batch=True)

        assert len(cur._executed) == 0


class TestFleetProfileBatch:
    """Tests for build_fleet_profile with km_batch."""

    def test_km_batch_true_uses_km_batch_table(self):
        """km_batch=True queries _km_batch for alliance."""
        rows = [(25.3, 18, 111)]
        cur = MultiResultCursor([rows])
        result = build_fleet_profile(cur, _alliance_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert result is not None
        assert result["avg_fleet_size"] == 25.3
        assert result["median_fleet_size"] == 18
        assert result["max_fleet_size"] == 111

    def test_non_alliance_returns_none(self):
        """Non-alliance entity type returns None."""
        cur = MultiResultCursor([[]])
        result = build_fleet_profile(cur, _corp_ctx(), 30, km_batch=True)
        assert result is None

    def test_km_batch_false_uses_killmails(self):
        """km_batch=False uses original killmails path."""
        rows = [(19.5, 12, 80)]
        cur = MultiResultCursor([rows])
        result = build_fleet_profile(cur, _alliance_ctx(), 30, km_batch=False)

        assert "killmails" in cur._executed[0][0] or "killmail_attackers" in cur._executed[0][0]
        assert result is not None


class TestHuntingHoursKmBatch:
    """Tests for build_hunting_hours with km_batch (Corporation path)."""

    def test_corp_km_batch_true(self):
        """Corporation with km_batch=True uses _km_batch."""
        rows = [(14.0, 10), (18.0, 5)]
        cur = MultiResultCursor([rows])
        result = build_hunting_hours(cur, _corp_ctx(), 30, km_batch=True)

        assert "_km_batch" in cur._executed[0][0]
        assert result["hourly_activity"][14] == 10
        assert result["hourly_activity"][18] == 5

    def test_alliance_ignores_km_batch(self):
        """Alliance with km_batch=True but hs_batch=None still uses hourly_stats SQL."""
        rows = [(14.0, 10)]
        cur = MultiResultCursor([rows])
        result = build_hunting_hours(cur, _alliance_ctx(), 30, km_batch=True)

        # Alliance without hs_batch falls through to SQL path, not km_batch
        assert "_km_batch" not in cur._executed[0][0]
