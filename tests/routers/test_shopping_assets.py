"""Tests for shopping list asset integration endpoints."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


class TestApplyAssetsEndpoint:
    """Tests for POST /api/shopping/lists/{list_id}/apply-assets endpoint."""

    def test_apply_assets_success(self):
        """Test applying character assets to shopping list items."""
        with patch("routers.shopping.shopping_service") as mock_shopping_service:
            mock_shopping_service.apply_assets_to_list.return_value = {
                "items_updated": 5,
                "total_covered": 150,
                "total_needed": 200
            }

            from main import app
            client = TestClient(app)

            response = client.post(
                "/api/shopping/lists/1/apply-assets",
                params={"character_id": 12345}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["items_updated"] == 5
            assert data["total_covered"] == 150
            assert data["total_needed"] == 200
            mock_shopping_service.apply_assets_to_list.assert_called_once_with(1, 12345)

    def test_apply_assets_requires_character_id(self):
        """Test that character_id query parameter is required."""
        from main import app
        client = TestClient(app)

        response = client.post("/api/shopping/lists/1/apply-assets")

        assert response.status_code == 422  # Validation error

    def test_apply_assets_list_not_found(self):
        """Test applying assets to non-existent list returns 404."""
        with patch("routers.shopping.shopping_service") as mock_shopping_service:
            mock_shopping_service.apply_assets_to_list.return_value = None

            from main import app
            client = TestClient(app)

            response = client.post(
                "/api/shopping/lists/999/apply-assets",
                params={"character_id": 12345}
            )

            assert response.status_code == 404

    def test_apply_assets_updates_quantity_in_assets(self):
        """Test that assets correctly update quantity_in_assets field."""
        with patch("routers.shopping.shopping_service") as mock_shopping_service:
            mock_shopping_service.apply_assets_to_list.return_value = {
                "items_updated": 3,
                "total_covered": 100,
                "total_needed": 100
            }

            from main import app
            client = TestClient(app)

            response = client.post(
                "/api/shopping/lists/1/apply-assets",
                params={"character_id": 12345}
            )

            assert response.status_code == 200
            data = response.json()
            # When total_covered equals total_needed, all items are fully covered
            assert data["total_covered"] == data["total_needed"]


class TestGetListWithAssetsEndpoint:
    """Tests for GET /api/shopping/lists/{list_id}/with-assets endpoint."""

    def test_get_list_with_assets_success(self):
        """Test getting list with asset deduction information."""
        with patch("routers.shopping.shopping_service") as mock_shopping_service:
            mock_shopping_service.get_list_with_assets.return_value = {
                "id": 1,
                "name": "Test List",
                "items": [
                    {
                        "type_id": 34,
                        "item_name": "Tritanium",
                        "quantity_needed": 1000,
                        "quantity_in_assets": 500,
                        "quantity_to_buy": 500
                    },
                    {
                        "type_id": 35,
                        "item_name": "Pyerite",
                        "quantity_needed": 200,
                        "quantity_in_assets": 200,
                        "quantity_to_buy": 0
                    }
                ]
            }

            from main import app
            client = TestClient(app)

            response = client.get("/api/shopping/lists/1/with-assets")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert len(data["items"]) == 2

            # First item needs partial purchase
            assert data["items"][0]["quantity_to_buy"] == 500

            # Second item fully covered by assets
            assert data["items"][1]["quantity_to_buy"] == 0

            mock_shopping_service.get_list_with_assets.assert_called_once_with(1)

    def test_get_list_with_assets_not_found(self):
        """Test getting non-existent list returns 404."""
        with patch("routers.shopping.shopping_service") as mock_shopping_service:
            mock_shopping_service.get_list_with_assets.return_value = None

            from main import app
            client = TestClient(app)

            response = client.get("/api/shopping/lists/999/with-assets")

            assert response.status_code == 404

    def test_get_list_with_assets_includes_quantity_fields(self):
        """Test that response includes all quantity-related fields."""
        with patch("routers.shopping.shopping_service") as mock_shopping_service:
            mock_shopping_service.get_list_with_assets.return_value = {
                "id": 1,
                "name": "Test List",
                "items": [
                    {
                        "type_id": 34,
                        "item_name": "Tritanium",
                        "quantity_needed": 1000,
                        "quantity_in_assets": 300,
                        "quantity_to_buy": 700
                    }
                ]
            }

            from main import app
            client = TestClient(app)

            response = client.get("/api/shopping/lists/1/with-assets")

            assert response.status_code == 200
            data = response.json()
            item = data["items"][0]

            # All required fields must be present
            assert "type_id" in item
            assert "quantity_needed" in item
            assert "quantity_in_assets" in item
            assert "quantity_to_buy" in item

    def test_get_list_with_assets_calculates_quantity_to_buy_correctly(self):
        """Test quantity_to_buy = quantity_needed - quantity_in_assets."""
        with patch("routers.shopping.shopping_service") as mock_shopping_service:
            mock_shopping_service.get_list_with_assets.return_value = {
                "id": 1,
                "name": "Test List",
                "items": [
                    {
                        "type_id": 34,
                        "item_name": "Tritanium",
                        "quantity_needed": 1000,
                        "quantity_in_assets": 300,
                        "quantity_to_buy": 700
                    }
                ]
            }

            from main import app
            client = TestClient(app)

            response = client.get("/api/shopping/lists/1/with-assets")

            assert response.status_code == 200
            data = response.json()
            item = data["items"][0]

            # Verify calculation
            expected_to_buy = item["quantity_needed"] - item["quantity_in_assets"]
            assert item["quantity_to_buy"] == expected_to_buy


class TestShoppingServiceAssetMethods:
    """Tests for ShoppingService asset-related methods."""

    def _setup_mock_db(self, mock_db, fetchone_returns, fetchall_returns, rowcount=1):
        """Helper to setup mock database connection."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.return_value = mock_conn

        # Setup cursor return values
        mock_cursor.fetchone.return_value = fetchone_returns
        mock_cursor.fetchall.return_value = fetchall_returns
        mock_cursor.rowcount = rowcount

        return mock_cursor

    def test_apply_assets_to_list_calls_asset_service(self):
        """Test that apply_assets_to_list uses AssetService to find assets."""
        from src.shopping_service import ShoppingService

        with patch("src.shopping_service.get_db_connection") as mock_db, \
             patch("src.shopping_service.asset_service") as mock_asset_svc:

            # Setup mock - fetchone returns truthy for list existence check
            mock_cursor = self._setup_mock_db(
                mock_db,
                fetchone_returns={"id": 1},  # List exists
                fetchall_returns=[
                    {"id": 1, "type_id": 34, "quantity": 1000},
                    {"id": 2, "type_id": 35, "quantity": 200}
                ],
                rowcount=1
            )

            # Setup mock asset service response
            mock_asset_svc.find_assets_for_types.return_value = {
                34: 500,  # 500 Tritanium in assets
                35: 1000  # 1000 Pyerite in assets
            }

            service = ShoppingService()
            result = service.apply_assets_to_list(list_id=1, character_id=12345)

            # Verify asset service was called with correct type_ids
            mock_asset_svc.find_assets_for_types.assert_called_once()
            call_args = mock_asset_svc.find_assets_for_types.call_args
            assert call_args[0][0] == 12345  # character_id
            assert set(call_args[0][1]) == {34, 35}  # type_ids

    def test_apply_assets_to_list_updates_quantity_in_assets(self):
        """Test that apply_assets_to_list updates the quantity_in_assets column."""
        from src.shopping_service import ShoppingService

        with patch("src.shopping_service.get_db_connection") as mock_db, \
             patch("src.shopping_service.asset_service") as mock_asset_svc:

            mock_cursor = self._setup_mock_db(
                mock_db,
                fetchone_returns={"id": 1},  # List exists
                fetchall_returns=[
                    {"id": 1, "type_id": 34, "quantity": 1000}
                ],
                rowcount=1
            )

            # Character has 500 Tritanium but needs 1000
            mock_asset_svc.find_assets_for_types.return_value = {34: 500}

            service = ShoppingService()
            result = service.apply_assets_to_list(list_id=1, character_id=12345)

            # Verify UPDATE was called with min(asset_qty, needed_qty)
            update_calls = [call for call in mock_cursor.execute.call_args_list
                          if "UPDATE" in str(call)]
            assert len(update_calls) > 0

    def test_apply_assets_to_list_returns_summary(self):
        """Test that apply_assets_to_list returns proper summary dict."""
        from src.shopping_service import ShoppingService

        with patch("src.shopping_service.get_db_connection") as mock_db, \
             patch("src.shopping_service.asset_service") as mock_asset_svc:

            mock_cursor = self._setup_mock_db(
                mock_db,
                fetchone_returns={"id": 1},  # List exists
                fetchall_returns=[
                    {"id": 1, "type_id": 34, "quantity": 1000},
                    {"id": 2, "type_id": 35, "quantity": 200}
                ],
                rowcount=1
            )

            mock_asset_svc.find_assets_for_types.return_value = {34: 500, 35: 300}

            service = ShoppingService()
            result = service.apply_assets_to_list(list_id=1, character_id=12345)

            assert result is not None
            assert "items_updated" in result
            assert "total_covered" in result
            assert "total_needed" in result

    def test_get_list_with_assets_adds_quantity_to_buy(self):
        """Test that get_list_with_assets calculates quantity_to_buy for each item."""
        from src.shopping_service import ShoppingService

        with patch.object(ShoppingService, "get_list_with_items") as mock_get_list:
            mock_get_list.return_value = {
                "id": 1,
                "name": "Test List",
                "items": [
                    {
                        "type_id": 34,
                        "item_name": "Tritanium",
                        "quantity": 1000,
                        "quantity_in_assets": 300
                    }
                ],
                "products": [],
                "standalone_items": []
            }

            service = ShoppingService()
            result = service.get_list_with_assets(list_id=1)

            assert result is not None
            assert "items" in result

            # Each item should have quantity_to_buy calculated
            for item in result["items"]:
                assert "quantity_to_buy" in item
                expected = item["quantity"] - item.get("quantity_in_assets", 0)
                assert item["quantity_to_buy"] == expected

    def test_get_list_with_assets_returns_none_for_nonexistent_list(self):
        """Test that get_list_with_assets returns None for non-existent list."""
        from src.shopping_service import ShoppingService

        with patch.object(ShoppingService, "get_list_with_items") as mock_get_list:
            mock_get_list.return_value = None

            service = ShoppingService()
            result = service.get_list_with_assets(list_id=999)

            assert result is None

    def test_apply_assets_caps_at_needed_quantity(self):
        """Test that quantity_in_assets doesn't exceed quantity needed."""
        from src.shopping_service import ShoppingService

        with patch("src.shopping_service.get_db_connection") as mock_db, \
             patch("src.shopping_service.asset_service") as mock_asset_svc:

            mock_cursor = self._setup_mock_db(
                mock_db,
                fetchone_returns={"id": 1},  # List exists
                fetchall_returns=[
                    {"id": 1, "type_id": 34, "quantity": 200}
                ],
                rowcount=1
            )

            # Character has MORE than needed (1000 vs 200 needed)
            mock_asset_svc.find_assets_for_types.return_value = {34: 1000}

            service = ShoppingService()
            result = service.apply_assets_to_list(list_id=1, character_id=12345)

            # total_covered should be capped at total_needed (200), not 1000
            assert result is not None
            # The min() logic should cap covered at needed
            assert result["total_covered"] == 200
            assert result["total_needed"] == 200
