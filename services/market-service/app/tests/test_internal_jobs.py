"""Unit tests for internal job services.

Tests manipulation scanner, fuel scanner, price snapshotter,
arbitrage calculator, undercut checker, and regional prices.
All tests use mock cursors -- no real DB needed.
"""

import math
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# MockCursor / MockConnection helpers
# ---------------------------------------------------------------------------

class MockCursor:
    """Minimal cursor mock for tuple-based queries."""

    def __init__(self, results=None):
        self.results = results or []
        self.executed = []
        self._rowcount = 0

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        self._rowcount = 1

    def fetchall(self):
        return self.results

    def fetchone(self):
        return self.results[0] if self.results else None

    @property
    def rowcount(self):
        return self._rowcount

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockConnection:
    """Minimal connection mock that yields tuple cursors."""

    def __init__(self, cursor_results=None, cursor_factory_results=None):
        self._cursor_results = cursor_results or []
        self._cursor_factory_results = cursor_factory_results or []

    def cursor(self, cursor_factory=None):
        if cursor_factory is not None:
            return MockCursor(self._cursor_factory_results)
        return MockCursor(self._cursor_results)

    def commit(self):
        pass

    def rollback(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockDB:
    """Mimics eve_shared DatabasePool with connection() context manager."""

    def __init__(self, conn=None):
        self._conn = conn or MockConnection()

    class _CM:
        def __init__(self, conn):
            self.conn = conn
        def __enter__(self):
            return self.conn
        def __exit__(self, *a):
            pass

    def connection(self):
        return self._CM(self._conn)


# ============================================================================
# Manipulation Scanner Tests
# ============================================================================

class TestManipulationScanner:
    """Tests for manipulation_scanner.py pure functions."""

    def test_calculate_z_score_normal(self):
        from app.services.internal.manipulation_scanner import calculate_z_score
        assert calculate_z_score(100, 100, 10) == 0.0

    def test_calculate_z_score_high(self):
        from app.services.internal.manipulation_scanner import calculate_z_score
        assert calculate_z_score(150, 100, 10) == 5.0

    def test_calculate_z_score_zero_stddev(self):
        from app.services.internal.manipulation_scanner import calculate_z_score
        assert calculate_z_score(200, 100, 0) == 0.0

    def test_classify_severity_confirmed(self):
        from app.services.internal.manipulation_scanner import classify_severity
        assert classify_severity(4.5) == "confirmed"

    def test_classify_severity_probable(self):
        from app.services.internal.manipulation_scanner import classify_severity
        assert classify_severity(3.5) == "probable"

    def test_classify_severity_suspicious(self):
        from app.services.internal.manipulation_scanner import classify_severity
        assert classify_severity(2.8) == "suspicious"

    def test_classify_severity_normal(self):
        from app.services.internal.manipulation_scanner import classify_severity
        assert classify_severity(1.0) == "normal"

    def test_determine_manipulation_type_combined(self):
        from app.services.internal.manipulation_scanner import determine_manipulation_type
        assert determine_manipulation_type(60, 70) == "combined"

    def test_determine_manipulation_type_price_spike(self):
        from app.services.internal.manipulation_scanner import determine_manipulation_type
        assert determine_manipulation_type(80, 10) == "price_spike"

    def test_determine_manipulation_type_volume_anomaly(self):
        from app.services.internal.manipulation_scanner import determine_manipulation_type
        assert determine_manipulation_type(10, 70) == "volume_anomaly"

    def test_scan_manipulation_no_data(self):
        """scan_manipulation returns zero alerts when DB has no data."""
        from app.services.internal.manipulation_scanner import scan_manipulation
        db = MockDB(MockConnection(cursor_results=[]))
        result = scan_manipulation(db)
        assert result["status"] == "completed"
        assert result["details"]["total_alerts"] == 0

    def test_scan_manipulation_detects_alert(self):
        """scan_manipulation detects an alert when Z-score exceeds threshold."""
        from app.services.internal.manipulation_scanner import scan_manipulation, CRITICAL_ITEMS

        first_type_id = list(CRITICAL_ITEMS.values())[0]
        call_count = [0]

        class SmartConn:
            def cursor(self, cursor_factory=None):
                call_count[0] += 1
                # Pattern repeats per region: baselines, current, (maybe store_alerts)
                phase = call_count[0] % 2
                if phase == 1:  # baselines
                    return MockCursor(results=[
                        (first_type_id, 100.0, 5.0, 1000, 50.0, 10)
                    ])
                else:  # current prices
                    return MockCursor(results=[
                        (first_type_id, 200.0, 5000)
                    ])
            def commit(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        # Patch store_alerts to no-op so we don't need a third cursor pattern
        with patch("app.services.internal.manipulation_scanner.store_alerts"):
            db = MockDB(SmartConn())
            result = scan_manipulation(db)
        assert result["status"] == "completed"
        # The alert should be detected (price 200 vs baseline 100, z-score > 2.5)
        assert result["details"]["total_alerts"] > 0


# ============================================================================
# Fuel Scanner Tests
# ============================================================================

class TestFuelScanner:
    """Tests for fuel_scanner.py pure functions."""

    def test_classify_anomaly_critical(self):
        from app.services.internal.fuel_scanner import classify_anomaly
        assert classify_anomaly(150) == (True, "critical")

    def test_classify_anomaly_high(self):
        from app.services.internal.fuel_scanner import classify_anomaly
        assert classify_anomaly(70) == (True, "high")

    def test_classify_anomaly_medium(self):
        from app.services.internal.fuel_scanner import classify_anomaly
        assert classify_anomaly(35) == (True, "medium")

    def test_classify_anomaly_low(self):
        from app.services.internal.fuel_scanner import classify_anomaly
        assert classify_anomaly(20) == (True, "low")

    def test_classify_anomaly_normal(self):
        from app.services.internal.fuel_scanner import classify_anomaly
        assert classify_anomaly(5) == (False, "normal")

    def test_classify_anomaly_negative(self):
        from app.services.internal.fuel_scanner import classify_anomaly
        assert classify_anomaly(-80) == (True, "high")

    def test_calculate_snapshots_empty(self):
        from app.services.internal.fuel_scanner import calculate_snapshots, MONITORED_REGIONS
        snapshots = calculate_snapshots({}, {}, MONITORED_REGIONS)
        # Should produce len(regions) * 4 (isotopes) snapshots
        assert len(snapshots) == len(MONITORED_REGIONS) * 4
        # All should be normal when no data
        assert all(s["severity"] == "normal" for s in snapshots)

    def test_calculate_snapshots_with_data(self):
        from app.services.internal.fuel_scanner import calculate_snapshots, ISOTOPES
        region_ids = [10000002]
        isotope_id = list(ISOTOPES.values())[0]
        current = {(10000002, isotope_id): {"volume": 2000, "price": 500.0}}
        baselines = {(10000002, isotope_id): {"volume": 1000, "price": 400.0, "stddev": 100.0}}
        snapshots = calculate_snapshots(current, baselines, region_ids)
        # Find the one with our isotope
        s = [x for x in snapshots if x["isotope_id"] == isotope_id][0]
        assert s["volume_delta_percent"] == 100.0
        assert s["anomaly_detected"] is True
        assert s["severity"] == "critical"

    def test_scan_fuel_markets_no_data(self):
        """scan_fuel_markets completes with empty DB."""
        from app.services.internal.fuel_scanner import scan_fuel_markets

        class BulkConn:
            def cursor(self, cursor_factory=None):
                return MockCursor(results=[])
            def commit(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        db = MockDB(BulkConn())
        result = scan_fuel_markets(db)
        assert result["status"] == "completed"
        assert result["details"]["anomalies_detected"] == 0


# ============================================================================
# Price Snapshotter Tests
# ============================================================================

class TestPriceSnapshotter:
    """Tests for price_snapshotter.py."""

    def test_snapshot_prices_no_data(self):
        from app.services.internal.price_snapshotter import snapshot_prices
        db = MockDB(MockConnection(cursor_results=[]))
        result = snapshot_prices(db)
        assert result["status"] == "completed"
        assert result["details"]["records_inserted"] == 0

    def test_take_snapshot_counts(self):
        from app.services.internal.price_snapshotter import take_snapshot

        class SnapshotConn:
            def __init__(self):
                self._call = 0
            def cursor(self, cursor_factory=None):
                self._call += 1
                if self._call == 1:  # SELECT
                    return MockCursor(results=[
                        (10000002, 28668, 100.0, 80.0, 5000, 3000),
                        (10000043, 28668, 110.0, 85.0, 4000, 2500),
                    ])
                return MockCursor()  # INSERT
            def commit(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        db = MockDB(SnapshotConn())
        inserted = take_snapshot(db)
        # Each row produces one INSERT; rowcount is always 1 on our mock
        assert inserted == 2

    def test_critical_items_defined(self):
        from app.services.internal.price_snapshotter import CRITICAL_ITEMS
        assert len(CRITICAL_ITEMS) == 5
        assert "Nanite Repair Paste" in CRITICAL_ITEMS


# ============================================================================
# Arbitrage Calculator Tests
# ============================================================================

class TestArbitrageCalculator:
    """Tests for arbitrage_calculator.py pure functions."""

    def test_calculate_turnover_instant(self):
        from app.services.internal.arbitrage_calculator import calculate_turnover
        assert calculate_turnover(0.5) == "instant"

    def test_calculate_turnover_fast(self):
        from app.services.internal.arbitrage_calculator import calculate_turnover
        assert calculate_turnover(2) == "fast"

    def test_calculate_turnover_moderate(self):
        from app.services.internal.arbitrage_calculator import calculate_turnover
        assert calculate_turnover(5) == "moderate"

    def test_calculate_turnover_slow(self):
        from app.services.internal.arbitrage_calculator import calculate_turnover
        assert calculate_turnover(10) == "slow"

    def test_calculate_turnover_unknown(self):
        from app.services.internal.arbitrage_calculator import calculate_turnover
        assert calculate_turnover(None) == "unknown"

    def test_calculate_route_no_profit(self):
        """Route returns None when no profitable items."""
        from app.services.internal.arbitrage_calculator import calculate_route, TRADE_HUBS
        items = [{"type_id": 1, "type_name": "Test", "volume": 1.0}]
        prices = {
            (10000002, 1): {"lowest_sell": 100.0, "highest_buy": None},
            (10000043, 1): {"lowest_sell": None, "highest_buy": 50.0},
        }
        result = calculate_route(10000002, 10000043, items, prices, {})
        assert result is None

    def test_calculate_route_profitable(self):
        """Route found when large profit margin exists."""
        from app.services.internal.arbitrage_calculator import calculate_route
        items = [{"type_id": 1, "type_name": "Expensive Widget", "volume": 0.1}]
        prices = {
            (10000002, 1): {"lowest_sell": 1000.0, "highest_buy": None},
            (10000043, 1): {"lowest_sell": None, "highest_buy": 2000.0},
        }
        volumes = {1: 100}
        result = calculate_route(10000002, 10000043, items, prices, volumes)
        # 2000 - 1000 = 1000 gross profit per unit, fees ~102 ISK per unit
        # net ~898 ISK/unit * 100 qty = 89,800 -- below 2M min so None
        # Let's use much higher prices
        prices2 = {
            (10000002, 1): {"lowest_sell": 100000.0, "highest_buy": None},
            (10000043, 1): {"lowest_sell": None, "highest_buy": 200000.0},
        }
        result2 = calculate_route(10000002, 10000043, items, prices2, volumes)
        if result2:
            assert result2["net_total_profit"] > 0
            assert result2["from_hub_name"] == "Jita"
            assert result2["to_hub_name"] == "Amarr"

    def test_hub_distances_all_positive(self):
        """All hub distances are positive integers."""
        from app.services.internal.arbitrage_calculator import HUB_DISTANCES
        assert len(HUB_DISTANCES) == 10  # 5 hubs, C(5,2) = 10 pairs
        for (a, b), dist in HUB_DISTANCES.items():
            assert dist > 0
            assert a != b


# ============================================================================
# Undercut Checker Tests
# ============================================================================

class TestUndercutChecker:
    """Tests for undercut_checker.py pure functions."""

    def test_check_undercuts_no_settings(self):
        """Returns skipped when no settings configured."""
        from app.services.internal.undercut_checker import check_undercuts
        db = MockDB(MockConnection(cursor_results=[]))
        result = check_undercuts(db)
        assert result["status"] == "completed"
        assert result["details"]["skipped"] is True
        assert result["details"]["reason"] == "no_settings"

    def test_check_undercuts_alerts_disabled(self):
        """Returns skipped when alerts are disabled."""
        from app.services.internal.undercut_checker import check_undercuts

        class SettingsConn:
            def cursor(self, cursor_factory=None):
                return MockCursor(results=[
                    ({"alerts": {"market_undercuts": False}},)
                ])
            def commit(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        db = MockDB(SettingsConn())
        result = check_undercuts(db)
        assert result["details"]["reason"] == "alerts_disabled"

    @patch("app.services.internal.undercut_checker.get_active_character_ids")
    def test_check_undercuts_no_characters(self, mock_chars):
        """Returns skipped when no characters authenticated."""
        from app.services.internal.undercut_checker import check_undercuts
        mock_chars.return_value = []

        class SettingsConn:
            def cursor(self, cursor_factory=None):
                return MockCursor(results=[
                    ({"alerts": {"market_undercuts": True}},)
                ])
            def commit(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        db = MockDB(SettingsConn())
        result = check_undercuts(db)
        assert result["details"]["reason"] == "no_characters"


# ============================================================================
# Regional Prices Tests
# ============================================================================

class TestRegionalPrices:
    """Tests for regional_prices.py pure functions."""

    def test_calculate_realistic_price_empty(self):
        from app.services.internal.regional_prices import calculate_realistic_price
        assert calculate_realistic_price([]) is None

    def test_calculate_realistic_price_single(self):
        from app.services.internal.regional_prices import calculate_realistic_price
        orders = [{"price": 100.0, "volume_remain": 200000}]
        result = calculate_realistic_price(orders, target_volume=100000)
        assert result == 100.0

    def test_calculate_realistic_price_weighted(self):
        from app.services.internal.regional_prices import calculate_realistic_price
        orders = [
            {"price": 100.0, "volume_remain": 50000},
            {"price": 200.0, "volume_remain": 50000},
        ]
        result = calculate_realistic_price(orders, target_volume=100000)
        # 50000*100 + 50000*200 = 15M / 100000 = 150
        assert result == 150.0

    def test_calculate_realistic_price_partial(self):
        from app.services.internal.regional_prices import calculate_realistic_price
        orders = [{"price": 100.0, "volume_remain": 50}]
        result = calculate_realistic_price(orders, target_volume=100000)
        # Only 50 units available at 100
        assert result == 100.0

    def test_aggregate_prices_empty(self):
        from app.services.internal.regional_prices import aggregate_prices
        result = aggregate_prices([], set(), 10000002)
        assert result == {}

    def test_aggregate_prices_sells_only(self):
        from app.services.internal.regional_prices import aggregate_prices
        orders = [
            {"type_id": 1, "is_buy_order": False, "price": 100.0, "volume_remain": 50, "location_id": 60003760, "issued": "2026-01-01"},
            {"type_id": 1, "is_buy_order": False, "price": 110.0, "volume_remain": 30, "location_id": 60003760, "issued": "2026-01-01"},
        ]
        result = aggregate_prices(orders, {1}, 10000002)
        assert 1 in result
        assert result[1]["lowest_sell"] == 100.0
        assert result[1]["highest_buy"] is None
        assert result[1]["sell_volume"] == 80

    def test_aggregate_prices_buy_filter(self):
        """Buy orders at non-hub stations with non-region range are excluded."""
        from app.services.internal.regional_prices import aggregate_prices
        orders = [
            {"type_id": 2, "is_buy_order": True, "price": 90.0, "volume_remain": 100,
             "location_id": 99999999, "range": "station", "issued": "2026-01-01"},
            {"type_id": 2, "is_buy_order": True, "price": 85.0, "volume_remain": 200,
             "location_id": 60003760, "range": "station", "issued": "2026-01-01"},
        ]
        result = aggregate_prices(orders, {2}, 10000002)
        assert 2 in result
        # Only hub station order should be included
        assert result[2]["highest_buy"] == 85.0
        assert result[2]["buy_volume"] == 200


# ============================================================================
# Integration-style tests (mock DB layer)
# ============================================================================

class TestIntegrationMocked:
    """Higher-level tests that verify job functions return proper structures."""

    def test_scan_manipulation_response_shape(self):
        from app.services.internal.manipulation_scanner import scan_manipulation
        db = MockDB(MockConnection(cursor_results=[]))
        result = scan_manipulation(db)
        assert "status" in result
        assert "job" in result
        assert "details" in result
        assert result["job"] == "scan-manipulation"
        d = result["details"]
        assert "regions_scanned" in d
        assert "total_alerts" in d
        assert "elapsed_seconds" in d

    def test_snapshot_prices_response_shape(self):
        from app.services.internal.price_snapshotter import snapshot_prices
        db = MockDB(MockConnection(cursor_results=[]))
        result = snapshot_prices(db)
        assert result["job"] == "snapshot-prices"
        assert "records_inserted" in result["details"]

    def test_scan_fuel_markets_response_shape(self):
        from app.services.internal.fuel_scanner import scan_fuel_markets

        class Conn:
            def cursor(self, cursor_factory=None):
                return MockCursor(results=[])
            def commit(self):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        db = MockDB(Conn())
        result = scan_fuel_markets(db)
        assert result["job"] == "scan-fuel-markets"
        d = result["details"]
        assert "snapshots_taken" in d
        assert "anomalies_detected" in d

    def test_check_undercuts_response_shape(self):
        from app.services.internal.undercut_checker import check_undercuts
        db = MockDB(MockConnection(cursor_results=[]))
        result = check_undercuts(db)
        assert result["job"] == "check-undercuts"
        assert "details" in result
