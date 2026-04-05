"""Tests for batch calculator service."""
import math
from unittest.mock import MagicMock, patch

import pytest

from app.services.batch_calculator import BatchCalculator, SELL_FEE_PCT, EXCLUDED_TYPE_IDS


# --- Fixtures ---

class MockConnection:
    """Mock connection with cursor factory."""
    def __init__(self, cursor=None):
        self._cursor = cursor
        self.encoding = "UTF8"

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockCursor:
    """Mock cursor that returns predefined results."""
    def __init__(self, results=None):
        self.results = results or []
        self.executed = []
        self.connection = MockConnection(self)

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def mogrify(self, sql, params=None):
        """Required by psycopg2.extras.execute_values."""
        if params is None:
            return sql.encode("utf-8")
        # Simple placeholder replacement for testing
        result = sql
        if isinstance(params, (list, tuple)):
            for p in params:
                result = result.replace("%s", repr(p), 1)
        return result.encode("utf-8")

    def fetchall(self):
        return self.results

    def fetchone(self):
        return self.results[0] if self.results else None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockDB:
    """Mock database pool."""
    def __init__(self, cursors=None):
        self._cursors = cursors or [MockCursor()]
        self._idx = 0

    def connection(self):
        cursor = self._cursors[self._idx % len(self._cursors)]
        self._idx += 1
        return MockConnection(cursor)


# --- Unit Tests ---

class TestFetchAdjustedPrices:
    """Tests for ESI price fetching."""

    @patch("app.services.batch_calculator.httpx")
    def test_returns_price_dict(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"type_id": 34, "adjusted_price": 5.0, "average_price": 5.5},
            {"type_id": 35, "adjusted_price": 10.0, "average_price": 11.0},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        calc = BatchCalculator(MockDB())
        prices = calc._fetch_adjusted_prices()

        assert prices == {34: 5.0, 35: 10.0}

    @patch("app.services.batch_calculator.httpx")
    def test_skips_zero_prices(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"type_id": 34, "adjusted_price": 5.0},
            {"type_id": 99, "adjusted_price": 0},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        calc = BatchCalculator(MockDB())
        prices = calc._fetch_adjusted_prices()

        assert 99 not in prices
        assert prices[34] == 5.0

    @patch("app.services.batch_calculator.httpx")
    def test_returns_empty_on_error(self, mock_httpx):
        mock_httpx.get.side_effect = Exception("Connection refused")

        calc = BatchCalculator(MockDB())
        prices = calc._fetch_adjusted_prices()

        assert prices == {}


class TestGetAllT1Blueprints:
    """Tests for SDE blueprint loading."""

    def test_loads_blueprints(self):
        cursor = MockCursor(results=[
            (100, 200, "Rifter", "Frigate", "Ship"),
            (101, 201, "Ammo", "Projectile Ammo", "Charge"),
        ])
        calc = BatchCalculator(MockDB([cursor]))
        bps = calc._get_all_t1_blueprints()

        assert len(bps) == 2
        assert bps[0]["blueprint_id"] == 100
        assert bps[0]["product_id"] == 200
        assert bps[0]["product_name"] == "Rifter"

    def test_excludes_blocked_type_ids(self):
        excluded_id = list(EXCLUDED_TYPE_IDS)[0]
        cursor = MockCursor(results=[
            (100, excluded_id, "Blocked Item", "Group", "Category"),
            (101, 201, "Good Item", "Group", "Category"),
        ])
        calc = BatchCalculator(MockDB([cursor]))
        bps = calc._get_all_t1_blueprints()

        assert len(bps) == 1
        assert bps[0]["product_id"] == 201


class TestGetAllMaterials:
    """Tests for batch material loading."""

    def test_groups_by_blueprint(self):
        cursor = MockCursor(results=[
            (100, 34, 1000),  # BP 100 needs 1000x Tritanium
            (100, 35, 500),   # BP 100 needs 500x Pyerite
            (101, 34, 2000),  # BP 101 needs 2000x Tritanium
        ])
        calc = BatchCalculator(MockDB([cursor]))
        mats = calc._get_all_materials()

        assert len(mats[100]) == 2
        assert len(mats[101]) == 1
        assert mats[100][0] == (34, 1000)


class TestCalculateOpportunity:
    """Tests for single opportunity calculation."""

    def test_profitable_item(self):
        bp = {
            "blueprint_id": 100,
            "product_id": 200,
            "product_name": "Rifter",
            "group_name": "Frigate",
            "category_name": "Ship",
        }
        prices = {200: 1000.0, 34: 1.0, 35: 2.0}
        materials = {100: [(34, 100), (35, 50)]}
        outputs = {(100, 200): 1}

        calc = BatchCalculator(MockDB())
        opp = calc._calculate_opportunity(bp, prices, materials, outputs, me=10)

        assert opp is not None
        # ME=10: ceil(100 * 0.9) = 90, ceil(50 * 0.9) = 45
        expected_cost = 90 * 1.0 + 45 * 2.0  # 90 + 90 = 180
        assert opp["cheapest_material_cost"] == expected_cost
        assert opp["best_sell_price"] == 1000.0
        assert opp["profit"] == round(1000.0 - expected_cost, 2)
        assert opp["roi"] > 0

    def test_no_product_price(self):
        bp = {
            "blueprint_id": 100, "product_id": 200,
            "product_name": "X", "group_name": "G", "category_name": "C",
        }
        prices = {34: 1.0}  # No price for product 200
        materials = {100: [(34, 100)]}
        outputs = {}

        calc = BatchCalculator(MockDB())
        opp = calc._calculate_opportunity(bp, prices, materials, outputs, me=10)

        assert opp is None

    def test_missing_material_price(self):
        bp = {
            "blueprint_id": 100, "product_id": 200,
            "product_name": "X", "group_name": "G", "category_name": "C",
        }
        prices = {200: 1000.0}  # No price for material 34
        materials = {100: [(34, 100)]}
        outputs = {}

        calc = BatchCalculator(MockDB())
        opp = calc._calculate_opportunity(bp, prices, materials, outputs, me=10)

        assert opp is None

    def test_negative_roi_filtered(self):
        bp = {
            "blueprint_id": 100, "product_id": 200,
            "product_name": "X", "group_name": "G", "category_name": "C",
        }
        # Product costs 10, materials cost 100 → negative ROI
        prices = {200: 10.0, 34: 100.0}
        materials = {100: [(34, 100)]}
        outputs = {(100, 200): 1}

        calc = BatchCalculator(MockDB())
        opp = calc._calculate_opportunity(bp, prices, materials, outputs, me=10)

        assert opp is None

    def test_me_formula(self):
        """ME=10 should reduce material quantity by 10%, ceil to integer, min 1."""
        bp = {
            "blueprint_id": 100, "product_id": 200,
            "product_name": "X", "group_name": "G", "category_name": "C",
        }
        prices = {200: 1000000.0, 34: 1.0}
        # Base qty=1 → ceil(1 * 0.9) = ceil(0.9) = 1 (min 1)
        materials = {100: [(34, 1)]}
        outputs = {(100, 200): 1}

        calc = BatchCalculator(MockDB())
        opp = calc._calculate_opportunity(bp, prices, materials, outputs, me=10)

        assert opp is not None
        assert opp["cheapest_material_cost"] == 1.0  # max(1, ceil(0.9)) = 1

    def test_output_quantity_multiplier(self):
        bp = {
            "blueprint_id": 100, "product_id": 200,
            "product_name": "Ammo", "group_name": "Ammo", "category_name": "Charge",
        }
        prices = {200: 10.0, 34: 1.0}
        materials = {100: [(34, 100)]}
        outputs = {(100, 200): 100}  # Makes 100 per run

        calc = BatchCalculator(MockDB())
        opp = calc._calculate_opportunity(bp, prices, materials, outputs, me=10)

        assert opp is not None
        assert opp["best_sell_price"] == 10.0 * 100  # 1000

    def test_no_materials_returns_none(self):
        bp = {
            "blueprint_id": 999, "product_id": 200,
            "product_name": "X", "group_name": "G", "category_name": "C",
        }
        prices = {200: 1000.0}
        materials = {}  # BP 999 not in materials dict
        outputs = {}

        calc = BatchCalculator(MockDB())
        opp = calc._calculate_opportunity(bp, prices, materials, outputs, me=10)

        assert opp is None


class TestSaveOpportunities:
    """Tests for DB save + enrichment."""

    def test_empty_list_returns_zero(self):
        calc = BatchCalculator(MockDB())
        assert calc._save_opportunities([]) == 0

    def test_saves_and_enriches(self):
        cursor = MockCursor()
        calc = BatchCalculator(MockDB([cursor]))

        opps = [{
            "product_id": 200, "blueprint_id": 100,
            "product_name": "Rifter", "category": "Ship",
            "group_name": "Frigate", "difficulty": 50,
            "material_cost_jita": 100, "material_cost_amarr": 100,
            "material_cost_rens": 100, "material_cost_dodixie": 100,
            "material_cost_hek": 100,
            "cheapest_material_cost": 100, "cheapest_material_region": "the_forge",
            "sell_price_jita": 200, "sell_price_amarr": 200,
            "sell_price_rens": 200, "sell_price_dodixie": 200,
            "sell_price_hek": 200,
            "best_sell_price": 200, "best_sell_region": "the_forge",
            "profit": 100, "roi": 100.0, "me_level": 10,
        }]

        saved = calc._save_opportunities(opps)

        assert saved == 1
        # Should have: TRUNCATE, batch INSERT (via execute_values), enrichment UPDATE, fallback UPDATE
        assert len(cursor.executed) >= 3
        # execute_values passes bytes, regular execute passes str
        def _sql_contains(sql, needle):
            if isinstance(sql, bytes):
                return needle.encode() in sql
            return needle in sql

        assert _sql_contains(cursor.executed[0][0], "TRUNCATE")
        has_insert = any(_sql_contains(sql, "INSERT") for sql, _ in cursor.executed)
        has_enrichment = any(_sql_contains(sql, "market_prices") for sql, _ in cursor.executed)
        assert has_insert
        assert has_enrichment


class TestSellFeeConstant:
    """Test fee constants."""

    def test_sell_fee_is_5_1_percent(self):
        assert SELL_FEE_PCT == 0.051

    def test_net_profit_formula(self):
        """Net = sell * (1 - fee) - cost"""
        sell = 1000.0
        cost = 500.0
        net = sell * (1 - SELL_FEE_PCT) - cost
        assert round(net, 2) == 449.0  # 1000 * 0.949 - 500 = 449


class TestRunIntegration:
    """Test the full run() method with mocked ESI."""

    @patch("app.services.batch_calculator.httpx")
    def test_run_end_to_end(self, mock_httpx):
        # Mock ESI prices
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"type_id": 200, "adjusted_price": 1000.0},
            {"type_id": 34, "adjusted_price": 5.0},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        # Mock DB: blueprints query, materials query, outputs query, save ops
        bp_cursor = MockCursor(results=[
            (100, 200, "Rifter", "Frigate", "Ship"),
        ])
        mat_cursor = MockCursor(results=[
            (100, 34, 100),
        ])
        out_cursor = MockCursor(results=[
            (100, 200, 1),
        ])
        save_cursor = MockCursor()

        db = MockDB([bp_cursor, mat_cursor, out_cursor, save_cursor])
        calc = BatchCalculator(db)
        result = calc.run(me=10)

        assert result["status"] == "completed"
        assert result["details"]["blueprints_scanned"] == 1
        assert result["details"]["opportunities_saved"] == 1

    @patch("app.services.batch_calculator.httpx")
    def test_run_fails_on_no_prices(self, mock_httpx):
        mock_httpx.get.side_effect = Exception("ESI down")

        calc = BatchCalculator(MockDB())
        result = calc.run()

        assert result["status"] == "error"
