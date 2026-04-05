"""Tests for DoctrineEngine."""

import pytest
from app.services.fitting_service import FittingItem
from app.services.doctrine_engine import normalize_doctrine_to_request, SLOT_FLAG_RANGES


class TestNormalization:
    """Tests for normalize_doctrine_to_request()."""

    def test_single_high_slot_module(self):
        doctrine = {
            "ship_type_id": 24690,
            "fitting_json": {
                "high": [{"type_id": 3170, "type_name": "Railgun", "quantity": 1}],
                "med": [], "low": [], "rig": [], "drones": [],
            },
        }
        req = normalize_doctrine_to_request(doctrine)
        assert req.ship_type_id == 24690
        assert len(req.items) == 1
        assert req.items[0].type_id == 3170
        assert req.items[0].flag == 27
        assert req.items[0].quantity == 1

    def test_quantity_expansion(self):
        """quantity: 4 expands into 4 items with sequential flags."""
        doctrine = {
            "ship_type_id": 24690,
            "fitting_json": {
                "high": [{"type_id": 3170, "type_name": "Railgun", "quantity": 4}],
                "med": [], "low": [], "rig": [], "drones": [],
            },
        }
        req = normalize_doctrine_to_request(doctrine)
        assert len(req.items) == 4
        flags = [item.flag for item in req.items]
        assert flags == [27, 28, 29, 30]
        assert all(item.type_id == 3170 for item in req.items)

    def test_multiple_module_types_in_slot(self):
        """Two different modules in high slots get sequential flags."""
        doctrine = {
            "ship_type_id": 24690,
            "fitting_json": {
                "high": [
                    {"type_id": 3170, "type_name": "Railgun", "quantity": 2},
                    {"type_id": 3186, "type_name": "Blaster", "quantity": 1},
                ],
                "med": [], "low": [], "rig": [], "drones": [],
            },
        }
        req = normalize_doctrine_to_request(doctrine)
        assert len(req.items) == 3
        assert req.items[0].flag == 27
        assert req.items[1].flag == 28
        assert req.items[2].flag == 29
        assert req.items[2].type_id == 3186

    def test_all_slot_types(self):
        """All slot types get correct flag ranges."""
        doctrine = {
            "ship_type_id": 24690,
            "fitting_json": {
                "high": [{"type_id": 1, "type_name": "H", "quantity": 1}],
                "med": [{"type_id": 2, "type_name": "M", "quantity": 1}],
                "low": [{"type_id": 3, "type_name": "L", "quantity": 1}],
                "rig": [{"type_id": 4, "type_name": "R", "quantity": 1}],
                "drones": [{"type_id": 5, "type_name": "D", "quantity": 5}],
            },
        }
        req = normalize_doctrine_to_request(doctrine)
        flags = {item.type_id: item.flag for item in req.items}
        assert flags[1] == 27  # high
        assert flags[2] == 19  # med
        assert flags[3] == 11  # low
        assert flags[4] == 92  # rig
        assert flags[5] == 87  # drone

    def test_drones_keep_grouped_quantity(self):
        """Drones stay as a single item with quantity > 1."""
        doctrine = {
            "ship_type_id": 24690,
            "fitting_json": {
                "high": [], "med": [], "low": [], "rig": [],
                "drones": [{"type_id": 2488, "type_name": "Hammerhead II", "quantity": 5}],
            },
        }
        req = normalize_doctrine_to_request(doctrine)
        assert len(req.items) == 1
        assert req.items[0].type_id == 2488
        assert req.items[0].flag == 87
        assert req.items[0].quantity == 5

    def test_overflow_protection(self):
        """More modules than slots are silently dropped."""
        doctrine = {
            "ship_type_id": 24690,
            "fitting_json": {
                "high": [{"type_id": 1, "type_name": "H", "quantity": 10}],
                "med": [], "low": [], "rig": [], "drones": [],
            },
        }
        req = normalize_doctrine_to_request(doctrine)
        assert len(req.items) == 8  # max 8 high slots (27-34)

    def test_empty_fitting(self):
        """Empty fitting produces empty items list."""
        doctrine = {
            "ship_type_id": 24690,
            "fitting_json": {"high": [], "med": [], "low": [], "rig": [], "drones": []},
        }
        req = normalize_doctrine_to_request(doctrine)
        assert req.ship_type_id == 24690
        assert len(req.items) == 0

    def test_missing_slot_keys(self):
        """Missing slot keys in JSONB are handled gracefully."""
        doctrine = {
            "ship_type_id": 24690,
            "fitting_json": {"high": [{"type_id": 1, "type_name": "H", "quantity": 1}]},
        }
        req = normalize_doctrine_to_request(doctrine)
        assert len(req.items) == 1


# --- Task 2 imports (appended) ---
from unittest.mock import MagicMock, patch
from app.tests.conftest import MockDB, MockCursor
from app.services.doctrine_engine import DoctrineEngine


class TestGetDoctrine:
    """Tests for DoctrineEngine._get_doctrine()."""

    def test_returns_doctrine_dict(self):
        doctrine_row = {
            "id": 1,
            "ship_type_id": 24690,
            "name": "Eagle Fleet",
            "fitting_json": '{"high": [], "med": [], "low": [], "rig": [], "drones": []}',
            "ship_name": "Eagle",
            "is_active": True,
        }
        db = MockDB(rows=[doctrine_row])
        engine = DoctrineEngine(db)
        result = engine._get_doctrine(1)
        assert result["id"] == 1
        assert result["ship_type_id"] == 24690
        assert isinstance(result["fitting_json"], dict)

    def test_returns_none_for_missing(self):
        db = MockDB(rows=[])
        engine = DoctrineEngine(db)
        result = engine._get_doctrine(999)
        assert result is None

    def test_parses_json_string(self):
        """fitting_json stored as text gets parsed to dict."""
        row = {
            "id": 1, "ship_type_id": 24690, "name": "Test",
            "fitting_json": '{"high": [{"type_id": 1, "type_name": "X", "quantity": 1}]}',
            "ship_name": "Eagle", "is_active": True,
        }
        db = MockDB(rows=[row])
        engine = DoctrineEngine(db)
        result = engine._get_doctrine(1)
        assert result["fitting_json"]["high"][0]["type_id"] == 1


class TestCalculateDoctrineStats:
    """Tests for DoctrineEngine.calculate_doctrine_stats()."""

    def test_calls_fitting_stats_service(self):
        doctrine_row = {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [{"type_id": 3170, "type_name": "Rail", "quantity": 1}], "med": [], "low": [], "rig": [], "drones": []}',
            "ship_name": "Eagle", "is_active": True,
        }
        db = MockDB(rows=[doctrine_row])
        engine = DoctrineEngine(db)

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"ship": {"type_id": 24690}}
        engine.fitting_stats = MagicMock()
        engine.fitting_stats.calculate_stats.return_value = mock_response

        result = engine.calculate_doctrine_stats(1)
        engine.fitting_stats.calculate_stats.assert_called_once()
        call_req = engine.fitting_stats.calculate_stats.call_args[0][0]
        assert call_req.ship_type_id == 24690
        assert len(call_req.items) == 1

    def test_with_character_id(self):
        doctrine_row = {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [], "med": [], "low": [], "rig": [], "drones": []}',
            "ship_name": "Eagle", "is_active": True,
        }
        db = MockDB(rows=[doctrine_row])
        engine = DoctrineEngine(db)

        mock_response = MagicMock()
        engine.fitting_stats = MagicMock()
        engine.fitting_stats.calculate_stats.return_value = mock_response

        engine.calculate_doctrine_stats(1, character_id=12345)
        call_req = engine.fitting_stats.calculate_stats.call_args[0][0]
        assert call_req.character_id == 12345

    def test_missing_doctrine_raises(self):
        db = MockDB(rows=[])
        engine = DoctrineEngine(db)
        with pytest.raises(ValueError, match="not found"):
            engine.calculate_doctrine_stats(999)


# --- Task 3 imports (appended) ---
from app.services.fitting_stats.models import (
    FittingStatsResponse, OffenseStats, DefenseStats, CapacitorStats,
    NavigationStats, TargetingStats, SlotUsage, ResourceUsage,
    FittingSkillRequirement,
)


def _make_stats_response(total_dps=100, total_ehp=10000, required_skills=None, **kwargs):
    """Helper to build a minimal FittingStatsResponse for testing."""
    return FittingStatsResponse(
        ship={"type_id": 24690, "name": "Eagle", "group_name": "Heavy Assault Cruiser"},
        slots=SlotUsage(),
        resources=ResourceUsage(),
        offense=OffenseStats(total_dps=total_dps),
        defense=DefenseStats(total_ehp=total_ehp),
        capacitor=CapacitorStats(stable=kwargs.get("cap_stable", True)),
        navigation=NavigationStats(),
        targeting=TargetingStats(),
        required_skills=required_skills or [],
        skill_source=kwargs.get("skill_source", "all_v"),
        character_id=kwargs.get("character_id"),
    )


class TestCheckReadiness:
    """Tests for DoctrineEngine.check_readiness()."""

    def _make_engine_with_dual_stats(self, allv_stats, char_stats, doctrine_row):
        db = MockDB(rows=[doctrine_row])
        engine = DoctrineEngine(db)
        def mock_calc(req):
            if req.character_id is None:
                return allv_stats
            return char_stats
        engine.fitting_stats = MagicMock()
        engine.fitting_stats.calculate_stats.side_effect = mock_calc
        return engine

    def _doctrine_row(self):
        return {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [], "med": [], "low": [], "rig": [], "drones": []}',
            "ship_name": "Eagle", "is_active": True,
        }

    def test_perfect_readiness(self):
        allv = _make_stats_response(total_dps=500, total_ehp=50000)
        char = _make_stats_response(total_dps=500, total_ehp=50000, character_id=123)
        engine = self._make_engine_with_dual_stats(allv, char, self._doctrine_row())

        result = engine.check_readiness(1, 123)
        assert result["can_fly"] is True
        assert result["dps_ratio"] == 1.0
        assert result["ehp_ratio"] == 1.0
        assert result["missing_skills"] == []

    def test_reduced_effectiveness(self):
        allv = _make_stats_response(total_dps=500, total_ehp=50000)
        char = _make_stats_response(total_dps=400, total_ehp=45000, character_id=123)
        engine = self._make_engine_with_dual_stats(allv, char, self._doctrine_row())

        result = engine.check_readiness(1, 123)
        assert result["dps_ratio"] == pytest.approx(0.8, abs=0.01)
        assert result["ehp_ratio"] == pytest.approx(0.9, abs=0.01)

    def test_missing_skills_detected(self):
        skills = [
            FittingSkillRequirement(skill_id=3300, skill_name="Gunnery", required_level=5, trained_level=4, required_by=["Eagle"]),
            FittingSkillRequirement(skill_id=3301, skill_name="Missiles", required_level=3, trained_level=3, required_by=["Eagle"]),
        ]
        allv = _make_stats_response(required_skills=[])
        char = _make_stats_response(required_skills=skills, character_id=123)
        engine = self._make_engine_with_dual_stats(allv, char, self._doctrine_row())

        result = engine.check_readiness(1, 123)
        assert result["can_fly"] is False
        assert len(result["missing_skills"]) == 1
        assert result["missing_skills"][0].skill_name == "Gunnery"

    def test_zero_dps_division_safe(self):
        allv = _make_stats_response(total_dps=0, total_ehp=50000)
        char = _make_stats_response(total_dps=0, total_ehp=45000, character_id=123)
        engine = self._make_engine_with_dual_stats(allv, char, self._doctrine_row())

        result = engine.check_readiness(1, 123)
        assert result["dps_ratio"] == 0.0


# --- Task 4 imports (appended) ---


class TestCheckCompliance:
    """Tests for DoctrineEngine.check_compliance()."""

    def _make_engine(self, doctrine_stats, km_stats, doctrine_row):
        db = MockDB(rows=[doctrine_row])
        engine = DoctrineEngine(db)
        call_count = [0]
        def mock_calc(req):
            call_count[0] += 1
            if call_count[0] == 1:
                return doctrine_stats
            return km_stats
        engine.fitting_stats = MagicMock()
        engine.fitting_stats.calculate_stats.side_effect = mock_calc
        return engine

    def _doctrine_row(self):
        return {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [], "med": [], "low": [], "rig": [], "drones": []}',
            "ship_name": "Eagle", "is_active": True,
        }

    def test_perfect_compliance(self):
        stats = _make_stats_response(total_dps=500, total_ehp=50000, cap_stable=True)
        engine = self._make_engine(stats, stats, self._doctrine_row())

        km_items = [{"type_id": 3170, "flag": 27}]
        result = engine.check_compliance(1, km_items)
        assert result["compliance_score"] == 1.0
        assert result["tank_match"] is True

    def test_lower_dps_reduces_score(self):
        doctrine_stats = _make_stats_response(total_dps=500, total_ehp=50000)
        km_stats = _make_stats_response(total_dps=250, total_ehp=50000)
        engine = self._make_engine(doctrine_stats, km_stats, self._doctrine_row())

        result = engine.check_compliance(1, [{"type_id": 1, "flag": 27}])
        # DPS ratio = 0.5 → 0.5*0.35 + 1.0*0.35 + 1.0*0.15 + 1.0*0.15 = 0.825
        assert result["compliance_score"] == pytest.approx(0.825, abs=0.01)

    def test_tank_type_mismatch(self):
        doctrine_stats = _make_stats_response(total_dps=500, total_ehp=50000)
        doctrine_stats.defense.tank_type = "shield"
        km_stats = _make_stats_response(total_dps=500, total_ehp=50000)
        km_stats.defense.tank_type = "armor"
        engine = self._make_engine(doctrine_stats, km_stats, self._doctrine_row())

        result = engine.check_compliance(1, [{"type_id": 1, "flag": 27}])
        assert result["tank_match"] is False
        # 1.0*0.35 + 1.0*0.35 + 0.5*0.15 + 1.0*0.15 = 0.925
        assert result["compliance_score"] == pytest.approx(0.925, abs=0.01)

    def test_score_capped_at_one(self):
        """Over-performing fit still caps at 1.0."""
        doctrine_stats = _make_stats_response(total_dps=200, total_ehp=20000)
        km_stats = _make_stats_response(total_dps=500, total_ehp=50000)
        engine = self._make_engine(doctrine_stats, km_stats, self._doctrine_row())

        result = engine.check_compliance(1, [{"type_id": 1, "flag": 27}])
        assert result["compliance_score"] == 1.0

    def test_zero_doctrine_dps_safe(self):
        doctrine_stats = _make_stats_response(total_dps=0, total_ehp=50000)
        km_stats = _make_stats_response(total_dps=100, total_ehp=50000)
        engine = self._make_engine(doctrine_stats, km_stats, self._doctrine_row())

        result = engine.check_compliance(1, [{"type_id": 1, "flag": 27}])
        assert result["compliance_score"] <= 1.0


# --- Task 5 imports (appended) ---


class TestGenerateBom:
    """Tests for DoctrineEngine.generate_bom()."""

    def _make_engine(self, doctrine_row):
        db = MockDB(rows=[doctrine_row])
        return DoctrineEngine(db)

    def test_single_ship(self):
        row = {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [], "med": [], "low": [], "rig": [], "drones": []}',
            "ship_name": "Eagle", "is_active": True,
        }
        engine = self._make_engine(row)
        bom = engine.generate_bom(1)
        assert len(bom) == 1
        assert bom[0]["type_id"] == 24690
        assert bom[0]["quantity"] == 1

    def test_fleet_multiplier(self):
        row = {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [{"type_id": 3170, "type_name": "Railgun", "quantity": 4}], "med": [], "low": [], "rig": [], "drones": []}',
            "ship_name": "Eagle", "is_active": True,
        }
        engine = self._make_engine(row)
        bom = engine.generate_bom(1, quantity=30)
        hull = next(b for b in bom if b["type_id"] == 24690)
        rail = next(b for b in bom if b["type_id"] == 3170)
        assert hull["quantity"] == 30
        assert rail["quantity"] == 120  # 4 per fit × 30 ships

    def test_drones_included(self):
        row = {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [], "med": [], "low": [], "rig": [], "drones": [{"type_id": 2488, "type_name": "Hammerhead II", "quantity": 5}]}',
            "ship_name": "Eagle", "is_active": True,
        }
        engine = self._make_engine(row)
        bom = engine.generate_bom(1)
        drone = next(b for b in bom if b["type_id"] == 2488)
        assert drone["quantity"] == 5

    def test_duplicate_modules_aggregated(self):
        """Same type_id in different slots aggregates quantity."""
        row = {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [{"type_id": 3170, "type_name": "Rail", "quantity": 2}], "med": [], "low": [{"type_id": 3170, "type_name": "Rail", "quantity": 1}], "rig": [], "drones": []}',
            "ship_name": "Eagle", "is_active": True,
        }
        engine = self._make_engine(row)
        bom = engine.generate_bom(1)
        rail = next(b for b in bom if b["type_id"] == 3170)
        assert rail["quantity"] == 3

    def test_sorted_by_name(self):
        row = {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [{"type_id": 1, "type_name": "Zephyr", "quantity": 1}, {"type_id": 2, "type_name": "Alpha", "quantity": 1}], "med": [], "low": [], "rig": [], "drones": []}',
            "ship_name": "Eagle", "is_active": True,
        }
        engine = self._make_engine(row)
        bom = engine.generate_bom(1)
        names = [b["type_name"] for b in bom]
        assert names == sorted(names)

    def test_missing_doctrine_raises(self):
        db = MockDB(rows=[])
        engine = DoctrineEngine(db)
        with pytest.raises(ValueError, match="not found"):
            engine.generate_bom(999)


# --- Task 6 imports (appended) ---


class MockRedis:
    """Minimal Redis mock for cache tests."""
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key)
    def set(self, key, value, ex=None):
        self.store[key] = value
    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)


class TestCaching:
    """Tests for DoctrineEngine Redis caching."""

    def _doctrine_row(self):
        return {
            "id": 1, "ship_type_id": 24690, "name": "Eagle Fleet",
            "fitting_json": '{"high": [], "med": [], "low": [], "rig": [], "drones": []}',
            "ship_name": "Eagle", "is_active": True,
        }

    def test_stats_cached_on_first_call(self):
        db = MockDB(rows=[self._doctrine_row()])
        redis = MockRedis()
        engine = DoctrineEngine(db, redis=redis)

        mock_response = _make_stats_response(total_dps=500)
        engine.fitting_stats = MagicMock()
        engine.fitting_stats.calculate_stats.return_value = mock_response

        engine.calculate_doctrine_stats(1)
        assert "doctrine-stats:1:all_v" in redis.store

    def test_cached_result_returned_without_recalc(self):
        db = MockDB(rows=[self._doctrine_row()])
        redis = MockRedis()
        engine = DoctrineEngine(db, redis=redis)

        mock_response = _make_stats_response(total_dps=500)
        engine.fitting_stats = MagicMock()
        engine.fitting_stats.calculate_stats.return_value = mock_response

        # First call — calculates
        engine.calculate_doctrine_stats(1)
        assert engine.fitting_stats.calculate_stats.call_count == 1

        # Second call — from cache
        engine.calculate_doctrine_stats(1)
        assert engine.fitting_stats.calculate_stats.call_count == 1

    def test_character_id_in_cache_key(self):
        db = MockDB(rows=[self._doctrine_row()])
        redis = MockRedis()
        engine = DoctrineEngine(db, redis=redis)

        mock_response = _make_stats_response(total_dps=500, character_id=123)
        engine.fitting_stats = MagicMock()
        engine.fitting_stats.calculate_stats.return_value = mock_response

        engine.calculate_doctrine_stats(1, character_id=123)
        assert "doctrine-stats:1:123" in redis.store
        assert "doctrine-stats:1:all_v" not in redis.store

    def test_no_redis_still_works(self):
        db = MockDB(rows=[self._doctrine_row()])
        engine = DoctrineEngine(db, redis=None)

        mock_response = _make_stats_response()
        engine.fitting_stats = MagicMock()
        engine.fitting_stats.calculate_stats.return_value = mock_response

        result = engine.calculate_doctrine_stats(1)
        assert result is not None
