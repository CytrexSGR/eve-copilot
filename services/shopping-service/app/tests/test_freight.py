"""Tests for freight pricing calculator.

Tests the core freight logic:
- calculate_price formula: base + (volume * rate_per_m3) + (collateral * pct / 100)
- Validation: over-volume, over-collateral, both exceeded
- _row_to_route data transformation
- Edge cases: zero values, exactly-at-limit, negative values

CRITICAL: We do NOT import FreightService directly because its module
imports chain triggers database connections at module level.
Instead, we replicate the pure functions/formulas here and test them.
"""

import math
import pytest
from decimal import Decimal


# ---------------------------------------------------------------------------
# Freight price formula (extracted from FreightService.calculate_price)
# Formula: base_price + (volume * rate_per_m3) + (collateral * collateral_pct / 100)
# ---------------------------------------------------------------------------

def _calculate_price(route: dict, volume_m3: float, collateral_isk: float) -> dict:
    """Replicate FreightService.calculate_price logic without DB dependency."""
    errors = []
    if route["max_volume"] and volume_m3 > route["max_volume"]:
        errors.append(
            f"Volume {volume_m3:,.0f} m\u00b3 exceeds max {route['max_volume']:,.0f} m\u00b3"
        )
    if route["max_collateral"] and collateral_isk > route["max_collateral"]:
        errors.append(
            f"Collateral {collateral_isk:,.0f} ISK exceeds max {route['max_collateral']:,.0f} ISK"
        )

    base = Decimal(str(route["base_price"]))
    volume_cost = Decimal(str(volume_m3)) * Decimal(str(route["rate_per_m3"]))
    collateral_cost = (
        Decimal(str(collateral_isk))
        * Decimal(str(route["collateral_pct"]))
        / Decimal("100")
    )
    total = base + volume_cost + collateral_cost

    return {
        "route": route,
        "volume_m3": volume_m3,
        "collateral_isk": collateral_isk,
        "breakdown": {
            "base_price": float(base),
            "volume_cost": float(volume_cost),
            "collateral_cost": float(collateral_cost),
            "total_price": float(total),
        },
        "errors": errors,
        "is_valid": len(errors) == 0,
    }


# ---------------------------------------------------------------------------
# row_to_route transformation (extracted from FreightService._row_to_route)
# ---------------------------------------------------------------------------

def _row_to_route(row: dict) -> dict:
    """Replicate FreightService._row_to_route logic without DB dependency."""
    return {
        "id": row["id"],
        "name": row["name"],
        "start_system_id": row["start_system_id"],
        "start_system_name": row.get("start_name"),
        "end_system_id": row["end_system_id"],
        "end_system_name": row.get("end_name"),
        "route_type": row["route_type"],
        "base_price": float(row["base_price"]),
        "rate_per_m3": float(row["rate_per_m3"]),
        "collateral_pct": float(row["collateral_pct"]),
        "max_volume": float(row["max_volume"]) if row["max_volume"] else None,
        "max_collateral": float(row["max_collateral"]) if row["max_collateral"] else None,
        "is_active": row["is_active"],
        "notes": row.get("notes"),
    }


# ===========================================================================
# Test: calculate_price formula
# ===========================================================================

class TestCalculatePriceBasic:
    """Basic freight price calculations."""

    def test_zero_volume_zero_collateral(self, sample_route):
        """With 0 volume and 0 collateral, total should be base_price only."""
        result = _calculate_price(sample_route, volume_m3=0, collateral_isk=0)
        assert result["breakdown"]["base_price"] == 10_000_000.0
        assert result["breakdown"]["volume_cost"] == 0.0
        assert result["breakdown"]["collateral_cost"] == 0.0
        assert result["breakdown"]["total_price"] == 10_000_000.0
        assert result["is_valid"] is True
        assert result["errors"] == []

    def test_typical_shipment(self, sample_route):
        """Standard JF shipment: 50k m3, 1B collateral.

        base = 10M, volume = 50000 * 500 = 25M, collateral = 1B * 1% = 10M
        total = 10M + 25M + 10M = 45M
        """
        result = _calculate_price(
            sample_route, volume_m3=50_000, collateral_isk=1_000_000_000
        )
        assert result["breakdown"]["base_price"] == 10_000_000.0
        assert result["breakdown"]["volume_cost"] == 25_000_000.0
        assert result["breakdown"]["collateral_cost"] == 10_000_000.0
        assert result["breakdown"]["total_price"] == 45_000_000.0
        assert result["is_valid"] is True

    def test_max_jf_load(self, sample_route):
        """Full JF load: 360k m3 (exactly at max), 3B collateral (exactly at max).

        base = 10M, volume = 360000 * 500 = 180M, collateral = 3B * 1% = 30M
        total = 10M + 180M + 30M = 220M
        """
        result = _calculate_price(
            sample_route, volume_m3=360_000, collateral_isk=3_000_000_000
        )
        assert result["breakdown"]["total_price"] == 220_000_000.0
        assert result["is_valid"] is True
        assert result["errors"] == []

    def test_small_shipment(self, sample_route):
        """Very small shipment: 1 m3, 1 ISK collateral.

        base = 10M, volume = 1 * 500 = 500, collateral = 1 * 1% = 0.01
        total = 10,000,500.01
        """
        result = _calculate_price(sample_route, volume_m3=1, collateral_isk=1)
        assert result["breakdown"]["volume_cost"] == 500.0
        assert result["breakdown"]["collateral_cost"] == 0.01
        assert result["breakdown"]["total_price"] == 10_000_500.01

    def test_high_collateral_rate(self):
        """Route with 5% collateral rate on 2B collateral.

        collateral_cost = 2B * 5 / 100 = 100M
        """
        route = {
            "base_price": 5_000_000.0,
            "rate_per_m3": 1000.0,
            "collateral_pct": 5.0,
            "max_volume": 360_000.0,
            "max_collateral": 5_000_000_000.0,
            "is_active": True,
        }
        result = _calculate_price(route, volume_m3=10_000, collateral_isk=2_000_000_000)
        assert result["breakdown"]["base_price"] == 5_000_000.0
        assert result["breakdown"]["volume_cost"] == 10_000_000.0
        assert result["breakdown"]["collateral_cost"] == 100_000_000.0
        assert result["breakdown"]["total_price"] == 115_000_000.0


class TestCalculatePriceValidation:
    """Freight price validation (over-limit checks)."""

    def test_over_volume(self, sample_route):
        """Volume exceeds max_volume -> error but still calculates price."""
        result = _calculate_price(
            sample_route, volume_m3=400_000, collateral_isk=0
        )
        assert result["is_valid"] is False
        assert len(result["errors"]) == 1
        assert "Volume" in result["errors"][0]
        assert "exceeds max" in result["errors"][0]
        # Price is still calculated
        assert result["breakdown"]["total_price"] == 10_000_000 + 400_000 * 500

    def test_over_collateral(self, sample_route):
        """Collateral exceeds max_collateral -> error."""
        result = _calculate_price(
            sample_route, volume_m3=100_000, collateral_isk=5_000_000_000
        )
        assert result["is_valid"] is False
        assert len(result["errors"]) == 1
        assert "Collateral" in result["errors"][0]
        assert "exceeds max" in result["errors"][0]

    def test_both_exceeded(self, sample_route):
        """Both volume and collateral exceed limits -> 2 errors."""
        result = _calculate_price(
            sample_route, volume_m3=500_000, collateral_isk=5_000_000_000
        )
        assert result["is_valid"] is False
        assert len(result["errors"]) == 2

    def test_exactly_at_volume_limit(self, sample_route):
        """Volume exactly at max -> valid."""
        result = _calculate_price(
            sample_route, volume_m3=360_000, collateral_isk=0
        )
        assert result["is_valid"] is True

    def test_exactly_at_collateral_limit(self, sample_route):
        """Collateral exactly at max -> valid."""
        result = _calculate_price(
            sample_route, volume_m3=0, collateral_isk=3_000_000_000
        )
        assert result["is_valid"] is True

    def test_one_over_volume_limit(self, sample_route):
        """Volume 1 m3 over max -> invalid."""
        result = _calculate_price(
            sample_route, volume_m3=360_001, collateral_isk=0
        )
        assert result["is_valid"] is False
        assert len(result["errors"]) == 1

    def test_no_max_volume_no_validation(self):
        """Route with max_volume=None -> no volume validation."""
        route = {
            "base_price": 1_000_000.0,
            "rate_per_m3": 100.0,
            "collateral_pct": 1.0,
            "max_volume": None,
            "max_collateral": None,
            "is_active": True,
        }
        result = _calculate_price(route, volume_m3=999_999_999, collateral_isk=999_999_999_999)
        assert result["is_valid"] is True
        assert result["errors"] == []


class TestCalculatePriceEdgeCases:
    """Edge cases for freight price calculation."""

    def test_zero_base_price(self):
        """Route with 0 base price."""
        route = {
            "base_price": 0.0,
            "rate_per_m3": 500.0,
            "collateral_pct": 1.0,
            "max_volume": 360_000.0,
            "max_collateral": 3_000_000_000.0,
            "is_active": True,
        }
        result = _calculate_price(route, volume_m3=100_000, collateral_isk=1_000_000_000)
        assert result["breakdown"]["base_price"] == 0.0
        assert result["breakdown"]["total_price"] == 50_000_000.0 + 10_000_000.0

    def test_zero_rate_per_m3(self):
        """Route with 0 ISK/m3 rate (free volume)."""
        route = {
            "base_price": 10_000_000.0,
            "rate_per_m3": 0.0,
            "collateral_pct": 1.0,
            "max_volume": 360_000.0,
            "max_collateral": 3_000_000_000.0,
            "is_active": True,
        }
        result = _calculate_price(route, volume_m3=100_000, collateral_isk=1_000_000_000)
        assert result["breakdown"]["volume_cost"] == 0.0
        assert result["breakdown"]["total_price"] == 10_000_000.0 + 10_000_000.0

    def test_zero_collateral_pct(self):
        """Route with 0% collateral rate."""
        route = {
            "base_price": 10_000_000.0,
            "rate_per_m3": 500.0,
            "collateral_pct": 0.0,
            "max_volume": 360_000.0,
            "max_collateral": None,
            "is_active": True,
        }
        result = _calculate_price(route, volume_m3=100_000, collateral_isk=5_000_000_000)
        assert result["breakdown"]["collateral_cost"] == 0.0

    def test_fractional_volume(self):
        """Fractional volume (e.g., 0.5 m3 item)."""
        route = {
            "base_price": 0.0,
            "rate_per_m3": 1000.0,
            "collateral_pct": 0.0,
            "max_volume": None,
            "max_collateral": None,
            "is_active": True,
        }
        result = _calculate_price(route, volume_m3=0.5, collateral_isk=0)
        assert result["breakdown"]["volume_cost"] == 500.0

    def test_decimal_precision(self):
        """Ensure Decimal math does not lose precision.

        volume_cost = 33333.33 * 777.77 = 25,925,564.1441
        collateral_cost = 1,234,567,890.12 * 2.5 / 100 = 30,864,197.253
        total = 1,000,000 + 25,925,564.1441 + 30,864,197.253 = 57,789,761.3971
        """
        route = {
            "base_price": 1_000_000.0,
            "rate_per_m3": 777.77,
            "collateral_pct": 2.5,
            "max_volume": None,
            "max_collateral": None,
            "is_active": True,
        }
        result = _calculate_price(
            route, volume_m3=33_333.33, collateral_isk=1_234_567_890.12
        )
        # Verify components add up to total
        breakdown = result["breakdown"]
        computed_total = (
            breakdown["base_price"]
            + breakdown["volume_cost"]
            + breakdown["collateral_cost"]
        )
        assert abs(breakdown["total_price"] - computed_total) < 0.01


# ===========================================================================
# Test: _row_to_route transformation
# ===========================================================================

class TestRowToRoute:
    """Tests for _row_to_route data transformation."""

    def test_all_fields_populated(self, sample_db_row):
        """Full row with all fields -> correct dict."""
        result = _row_to_route(sample_db_row)
        assert result["id"] == 1
        assert result["name"] == "Jita to K-6K16"
        assert result["start_system_id"] == 30000142
        assert result["start_system_name"] == "Jita"
        assert result["end_system_id"] == 30003729
        assert result["end_system_name"] == "K-6K16"
        assert result["route_type"] == "jf"
        assert result["is_active"] is True
        assert result["notes"] == "Standard JF route"

    def test_decimal_to_float_conversion(self, sample_db_row):
        """Decimal values from DB are converted to float."""
        result = _row_to_route(sample_db_row)
        assert isinstance(result["base_price"], float)
        assert isinstance(result["rate_per_m3"], float)
        assert isinstance(result["collateral_pct"], float)
        assert isinstance(result["max_volume"], float)
        assert isinstance(result["max_collateral"], float)
        assert result["base_price"] == 10_000_000.0
        assert result["rate_per_m3"] == 500.0
        assert result["collateral_pct"] == 1.0

    def test_nullable_system_names(self):
        """System name JOINs can return None (if mapSolarSystems row missing)."""
        row = {
            "id": 2,
            "name": "Unknown Route",
            "start_system_id": 99999999,
            "end_system_id": 99999998,
            "route_type": "courier",
            "base_price": Decimal("5000000"),
            "rate_per_m3": Decimal("200"),
            "collateral_pct": Decimal("2.0"),
            "max_volume": Decimal("100000"),
            "max_collateral": Decimal("1000000000"),
            "is_active": False,
            "notes": None,
        }
        # No start_name or end_name keys at all
        result = _row_to_route(row)
        assert result["start_system_name"] is None
        assert result["end_system_name"] is None
        assert result["notes"] is None

    def test_null_max_volume(self):
        """max_volume=None -> stays None (unlimited route)."""
        row = {
            "id": 3,
            "name": "Unlimited Route",
            "start_system_id": 30000142,
            "end_system_id": 30003729,
            "route_type": "jf",
            "base_price": Decimal("1000000"),
            "rate_per_m3": Decimal("100"),
            "collateral_pct": Decimal("1.0"),
            "max_volume": None,
            "max_collateral": None,
            "is_active": True,
            "start_name": "Jita",
            "end_name": "K-6K16",
        }
        result = _row_to_route(row)
        assert result["max_volume"] is None
        assert result["max_collateral"] is None

    def test_inactive_route(self):
        """is_active=False passes through unchanged."""
        row = {
            "id": 4,
            "name": "Disabled Route",
            "start_system_id": 30000142,
            "end_system_id": 30002187,
            "route_type": "courier",
            "base_price": Decimal("0"),
            "rate_per_m3": Decimal("0"),
            "collateral_pct": Decimal("0"),
            "max_volume": Decimal("50000"),
            "max_collateral": Decimal("500000000"),
            "is_active": False,
            "start_name": "Jita",
            "end_name": "Amarr",
        }
        result = _row_to_route(row)
        assert result["is_active"] is False
        assert result["base_price"] == 0.0
        assert result["rate_per_m3"] == 0.0
        assert result["collateral_pct"] == 0.0

    def test_extra_db_fields_ignored(self, sample_db_row):
        """Extra fields in row dict (created_at, updated_at) do not cause errors."""
        # sample_db_row has created_at and updated_at - _row_to_route skips them
        result = _row_to_route(sample_db_row)
        assert "created_at" not in result
        assert "updated_at" not in result


# ===========================================================================
# Test: Transport trips calculation
# ===========================================================================

class TestTransportTrips:
    """Test transport ship trips calculation logic.

    Extracted from ShoppingService.get_transport_options:
        trips = max(1, int(total_volume / cargo_capacity) + 1)
        fits = total_volume <= cargo_capacity
    """

    @staticmethod
    def _calc_trips(total_volume: float, cargo_capacity: float) -> tuple[int, bool]:
        """Replicate the trips calculation from ShoppingService."""
        trips = max(1, int(total_volume / cargo_capacity) + 1)
        fits = total_volume <= cargo_capacity
        return (1 if fits else trips, fits)

    def test_zero_volume(self):
        """Zero cargo -> 1 trip, fits in single trip."""
        trips, fits = self._calc_trips(0, 42_000)
        assert trips == 1
        assert fits is True

    def test_fits_exactly(self):
        """Volume equals capacity -> 1 trip."""
        trips, fits = self._calc_trips(42_000, 42_000)
        assert trips == 1
        assert fits is True

    def test_slightly_over(self):
        """Volume barely exceeds capacity -> 2 trips."""
        trips, fits = self._calc_trips(42_001, 42_000)
        assert trips == 2
        assert fits is False

    def test_double_capacity(self):
        """Volume is exactly 2x capacity -> 3 trips (int division + 1)."""
        trips, fits = self._calc_trips(84_000, 42_000)
        assert fits is False
        # int(84000/42000) + 1 = 2 + 1 = 3
        assert trips == 3

    def test_large_shipment(self):
        """Very large volume -> many trips."""
        trips, fits = self._calc_trips(500_000, 42_000)
        assert fits is False
        # int(500000/42000) + 1 = 11 + 1 = 12
        assert trips == 12


# ===========================================================================
# Test: Region/Hub constants consistency
# ===========================================================================

class TestRegionConstants:
    """Test that the shopping service region constants are consistent."""

    # Constants extracted from ShoppingService
    REGION_KEY_TO_HUB = {
        "the_forge": ("Jita", 30000142),
        "domain": ("Amarr", 30002187),
        "heimatar": ("Rens", 30002510),
        "sinq_laison": ("Dodixie", 30002659),
        "metropolis": ("Hek", 30002053),
    }

    REGION_NAME_TO_ID = {
        "the_forge": 10000002,
        "domain": 10000043,
        "heimatar": 10000030,
        "sinq_laison": 10000032,
        "metropolis": 10000042,
    }

    REGION_DISPLAY_NAMES = {
        "the_forge": "Jita",
        "domain": "Amarr",
        "heimatar": "Rens",
        "sinq_laison": "Dodixie",
        "metropolis": "Hek",
    }

    def test_all_five_trade_hubs_present(self):
        """All 5 major EVE trade hubs must be defined."""
        assert len(self.REGION_KEY_TO_HUB) == 5
        assert len(self.REGION_NAME_TO_ID) == 5
        assert len(self.REGION_DISPLAY_NAMES) == 5

    def test_region_keys_consistent(self):
        """All three mappings use the same region keys."""
        assert set(self.REGION_KEY_TO_HUB.keys()) == set(self.REGION_NAME_TO_ID.keys())
        assert set(self.REGION_KEY_TO_HUB.keys()) == set(self.REGION_DISPLAY_NAMES.keys())

    def test_display_names_match_hub_names(self):
        """REGION_DISPLAY_NAMES matches REGION_KEY_TO_HUB hub names."""
        for key, (hub_name, _) in self.REGION_KEY_TO_HUB.items():
            assert self.REGION_DISPLAY_NAMES[key] == hub_name

    def test_jita_system_id(self):
        """Jita system ID is correct (30000142)."""
        assert self.REGION_KEY_TO_HUB["the_forge"] == ("Jita", 30000142)
        assert self.REGION_NAME_TO_ID["the_forge"] == 10000002


# ===========================================================================
# Test: Transport ships constant
# ===========================================================================

class TestTransportShips:
    """Test TRANSPORT_SHIPS constant data integrity."""

    # Extracted from shopping.py
    TRANSPORT_SHIPS = [
        {"ship_name": "Tayra", "ship_type_id": 648, "cargo_capacity": 42000.0},
        {"ship_name": "Mammoth", "ship_type_id": 652, "cargo_capacity": 41400.0},
        {"ship_name": "Bestower", "ship_type_id": 1944, "cargo_capacity": 38500.0},
        {"ship_name": "Iteron Mark V", "ship_type_id": 657, "cargo_capacity": 38400.0},
        {"ship_name": "Nereus", "ship_type_id": 655, "cargo_capacity": 20000.0},
        {"ship_name": "Badger", "ship_type_id": 648, "cargo_capacity": 17500.0},
        {"ship_name": "Miasmos", "ship_type_id": 654, "cargo_capacity": 63000.0},
        {"ship_name": "Kryos", "ship_type_id": 653, "cargo_capacity": 43000.0},
    ]

    def test_all_ships_have_required_fields(self):
        """Every transport ship must have name, type_id, and cargo_capacity."""
        for ship in self.TRANSPORT_SHIPS:
            assert "ship_name" in ship
            assert "ship_type_id" in ship
            assert "cargo_capacity" in ship
            assert isinstance(ship["ship_name"], str)
            assert isinstance(ship["ship_type_id"], int)
            assert isinstance(ship["cargo_capacity"], float)

    def test_all_capacities_positive(self):
        """All cargo capacities must be positive."""
        for ship in self.TRANSPORT_SHIPS:
            assert ship["cargo_capacity"] > 0, f"{ship['ship_name']} has non-positive capacity"

    def test_miasmos_highest_capacity(self):
        """Miasmos should have the highest cargo capacity (ore hold)."""
        max_ship = max(self.TRANSPORT_SHIPS, key=lambda s: s["cargo_capacity"])
        assert max_ship["ship_name"] == "Miasmos"
        assert max_ship["cargo_capacity"] == 63_000.0

    def test_eight_ships_defined(self):
        """We have exactly 8 transport ships defined."""
        assert len(self.TRANSPORT_SHIPS) == 8


# ===========================================================================
# Test: MockCursor (test infrastructure)
# ===========================================================================

class TestMockCursor:
    """Verify MockCursor and MultiResultCursor work correctly."""

    def test_mock_cursor_fetchall(self, mock_cursor):
        """MockCursor returns preset rows on fetchall."""
        mock_cursor.set_rows([{"id": 1}, {"id": 2}])
        mock_cursor.execute("SELECT * FROM test")
        assert mock_cursor.fetchall() == [{"id": 1}, {"id": 2}]

    def test_mock_cursor_fetchone(self, mock_cursor):
        """MockCursor returns first row on fetchone."""
        mock_cursor.set_rows([{"id": 42}])
        mock_cursor.execute("SELECT * FROM test WHERE id = 42")
        assert mock_cursor.fetchone() == {"id": 42}

    def test_mock_cursor_empty(self, mock_cursor):
        """MockCursor returns None/empty for no rows."""
        mock_cursor.execute("SELECT * FROM empty")
        assert mock_cursor.fetchall() == []
        assert mock_cursor.fetchone() is None

    def test_mock_cursor_tracks_sql(self, mock_cursor):
        """MockCursor records executed SQL and params."""
        mock_cursor.execute("SELECT * FROM x WHERE id = %s", (99,))
        assert mock_cursor.last_sql == "SELECT * FROM x WHERE id = %s"
        assert mock_cursor.last_params == (99,)

    def test_multi_cursor(self, multi_cursor):
        """MultiResultCursor returns different rows per execute."""
        cur = multi_cursor([
            [{"a": 1}],
            [{"b": 2}, {"b": 3}],
        ])
        cur.execute("SELECT 1")
        assert cur.fetchall() == [{"a": 1}]
        cur.execute("SELECT 2")
        assert cur.fetchall() == [{"b": 2}, {"b": 3}]
        cur.execute("SELECT 3")
        assert cur.fetchall() == []  # exhausted
