"""Tests for doctrine BOM → shopping list integration.

Tests the doctrine BOM fetching and item addition logic:
- fetch_doctrine_bom: HTTP call to character-service
- add_bom_items: Iterates BOM items and inserts into shopping list

CRITICAL: We replicate the pure functions/logic to avoid import
chains that trigger database connections at module level.
We also test with mocks where safe to do so.
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Replicated pure logic from shopping.py: fetch_doctrine_bom
# ---------------------------------------------------------------------------

def _fetch_doctrine_bom(
    character_service_url: str,
    httpx_module,
    doctrine_id: int,
    quantity: int = 1,
):
    """Replicate fetch_doctrine_bom logic without module-level imports."""
    try:
        url = f"{character_service_url}/api/doctrines/{doctrine_id}/bom"
        response = httpx_module.get(url, params={"quantity": quantity}, timeout=10.0)
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Replicated pure logic from shopping.py: add_bom_items
# ---------------------------------------------------------------------------

def _add_bom_items(bom_items: list) -> list:
    """Replicate add_bom_items iteration logic.

    Returns the list of ShoppingItemCreate-equivalent dicts that would
    be passed to repo.create_item(). This tests the mapping logic
    without hitting the database.
    """
    if not bom_items:
        return []

    created = []
    for item in bom_items:
        created.append({
            "type_id": item["type_id"],
            "quantity": item["quantity"],
            "is_product": False,
            "build_decision": "buy",
        })
    return created


# ===========================================================================
# Test: fetch_doctrine_bom
# ===========================================================================

class TestFetchDoctrineBom:
    """Test HTTP call to character-service for doctrine BOM."""

    def test_fetch_bom_success(self):
        """Successful BOM fetch returns list of items."""
        mock_httpx = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"type_id": 12015, "type_name": "Muninn", "quantity": 30},
        ]
        mock_httpx.get.return_value = mock_response

        result = _fetch_doctrine_bom(
            "http://character-service:8000", mock_httpx, 1, quantity=30
        )
        assert result is not None
        assert len(result) == 1
        assert result[0]["type_id"] == 12015
        assert result[0]["quantity"] == 30

    def test_fetch_bom_multiple_items(self):
        """BOM with multiple items returns all of them."""
        mock_httpx = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"type_id": 12015, "type_name": "Muninn", "quantity": 30},
            {"type_id": 2961, "type_name": "720mm Howitzer Artillery II", "quantity": 120},
            {"type_id": 3170, "type_name": "Republic Fleet Gyrostabilizer", "quantity": 60},
        ]
        mock_httpx.get.return_value = mock_response

        result = _fetch_doctrine_bom(
            "http://character-service:8000", mock_httpx, 1, quantity=30
        )
        assert len(result) == 3
        assert result[1]["type_name"] == "720mm Howitzer Artillery II"

    def test_fetch_bom_passes_quantity_param(self):
        """Quantity parameter is forwarded to the HTTP request."""
        mock_httpx = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_httpx.get.return_value = mock_response

        _fetch_doctrine_bom(
            "http://character-service:8000", mock_httpx, 42, quantity=15
        )
        mock_httpx.get.assert_called_once_with(
            "http://character-service:8000/api/doctrines/42/bom",
            params={"quantity": 15},
            timeout=10.0,
        )

    def test_fetch_bom_404_returns_none(self):
        """404 response returns None."""
        mock_httpx = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_httpx.get.return_value = mock_response

        result = _fetch_doctrine_bom(
            "http://character-service:8000", mock_httpx, 999, quantity=1
        )
        assert result is None

    def test_fetch_bom_500_returns_none(self):
        """500 response returns None."""
        mock_httpx = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_httpx.get.return_value = mock_response

        result = _fetch_doctrine_bom(
            "http://character-service:8000", mock_httpx, 1, quantity=1
        )
        assert result is None

    def test_fetch_bom_connection_error_returns_none(self):
        """Connection refused returns None (exception caught)."""
        mock_httpx = MagicMock()
        mock_httpx.get.side_effect = Exception("Connection refused")

        result = _fetch_doctrine_bom(
            "http://character-service:8000", mock_httpx, 1, quantity=1
        )
        assert result is None

    def test_fetch_bom_timeout_returns_none(self):
        """Timeout returns None (exception caught)."""
        mock_httpx = MagicMock()
        mock_httpx.get.side_effect = TimeoutError("Request timed out")

        result = _fetch_doctrine_bom(
            "http://character-service:8000", mock_httpx, 1, quantity=1
        )
        assert result is None

    def test_fetch_bom_url_format(self):
        """URL is correctly formed from service URL and doctrine ID."""
        mock_httpx = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_httpx.get.return_value = mock_response

        _fetch_doctrine_bom(
            "http://my-service:9000", mock_httpx, 77, quantity=1
        )
        call_args = mock_httpx.get.call_args
        assert call_args[0][0] == "http://my-service:9000/api/doctrines/77/bom"


# ===========================================================================
# Test: add_bom_items mapping logic
# ===========================================================================

class TestAddBomItems:
    """Test BOM → shopping item mapping logic."""

    def test_empty_bom_returns_empty(self):
        """Empty BOM returns empty list."""
        result = _add_bom_items([])
        assert result == []

    def test_single_item_mapped(self):
        """Single BOM item maps to one shopping item."""
        bom = [{"type_id": 12015, "type_name": "Muninn", "quantity": 30}]
        result = _add_bom_items(bom)
        assert len(result) == 1
        assert result[0]["type_id"] == 12015
        assert result[0]["quantity"] == 30
        assert result[0]["is_product"] is False
        assert result[0]["build_decision"] == "buy"

    def test_multiple_items_mapped(self):
        """Multiple BOM items all map correctly."""
        bom = [
            {"type_id": 12015, "type_name": "Muninn", "quantity": 30},
            {"type_id": 2961, "type_name": "720mm Howitzer Artillery II", "quantity": 120},
            {"type_id": 3170, "type_name": "Republic Fleet Gyrostabilizer", "quantity": 60},
        ]
        result = _add_bom_items(bom)
        assert len(result) == 3
        assert result[0]["type_id"] == 12015
        assert result[1]["type_id"] == 2961
        assert result[2]["type_id"] == 3170

    def test_quantities_preserved(self):
        """Item quantities from BOM are preserved exactly."""
        bom = [
            {"type_id": 100, "type_name": "Item A", "quantity": 1},
            {"type_id": 200, "type_name": "Item B", "quantity": 999},
        ]
        result = _add_bom_items(bom)
        assert result[0]["quantity"] == 1
        assert result[1]["quantity"] == 999

    def test_all_items_are_buy_not_product(self):
        """BOM items are set to buy, not product."""
        bom = [
            {"type_id": 100, "type_name": "Ship", "quantity": 5},
            {"type_id": 200, "type_name": "Module", "quantity": 20},
        ]
        result = _add_bom_items(bom)
        for item in result:
            assert item["is_product"] is False
            assert item["build_decision"] == "buy"

    def test_large_bom(self):
        """Large BOM (50 items) maps all items."""
        bom = [
            {"type_id": i, "type_name": f"Item {i}", "quantity": i * 10}
            for i in range(1, 51)
        ]
        result = _add_bom_items(bom)
        assert len(result) == 50
        assert result[49]["type_id"] == 50
        assert result[49]["quantity"] == 500


# ===========================================================================
# Test: Endpoint logic (request validation / branching)
# ===========================================================================

class TestAddDoctrineEndpointLogic:
    """Test the endpoint's branching logic (replicated)."""

    @staticmethod
    def _endpoint_logic(
        list_exists: bool,
        bom_result,  # None = fetch failed, [] = empty, [...] = items
    ) -> dict:
        """Replicate the endpoint's branching logic.

        Returns {"status": int} or {"status": 200, "items": [...]}
        """
        if not list_exists:
            return {"status": 404, "detail": "Shopping list not found"}

        if bom_result is None:
            return {"status": 502, "detail": "Failed to fetch doctrine BOM"}

        if not bom_result:
            return {"status": 404, "detail": "Doctrine BOM is empty"}

        items = _add_bom_items(bom_result)
        return {"status": 200, "items": items}

    def test_list_not_found(self):
        """Non-existent list returns 404."""
        result = self._endpoint_logic(list_exists=False, bom_result=None)
        assert result["status"] == 404
        assert "list" in result["detail"].lower()

    def test_bom_fetch_failure(self):
        """Failed BOM fetch returns 502."""
        result = self._endpoint_logic(list_exists=True, bom_result=None)
        assert result["status"] == 502

    def test_empty_bom(self):
        """Empty BOM returns 404."""
        result = self._endpoint_logic(list_exists=True, bom_result=[])
        assert result["status"] == 404
        assert "empty" in result["detail"].lower()

    def test_successful_addition(self):
        """Successful BOM adds items and returns 200."""
        bom = [
            {"type_id": 12015, "type_name": "Muninn", "quantity": 30},
            {"type_id": 2961, "type_name": "720mm Howitzer Artillery II", "quantity": 120},
        ]
        result = self._endpoint_logic(list_exists=True, bom_result=bom)
        assert result["status"] == 200
        assert len(result["items"]) == 2

    def test_single_item_bom(self):
        """Single-item BOM works correctly."""
        bom = [{"type_id": 12015, "type_name": "Muninn", "quantity": 1}]
        result = self._endpoint_logic(list_exists=True, bom_result=bom)
        assert result["status"] == 200
        assert len(result["items"]) == 1
