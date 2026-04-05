"""Unit tests for tax profile repository."""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from src.services.production.tax_repository import TaxRepository
from src.services.production.tax_models import TaxProfile, TaxProfileCreate


class TestTaxRepository:
    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        return conn, cursor

    def test_get_all_returns_list(self, mock_connection):
        """get_all should return list of TaxProfile."""
        conn, cursor = mock_connection
        cursor.fetchall.return_value = [
            (1, "Default", None, Decimal("3.00"), Decimal("3.00"),
             Decimal("3.60"), True, None, None)
        ]

        repo = TaxRepository(conn)
        result = repo.get_all()

        assert len(result) == 1
        assert isinstance(result[0], TaxProfile)
        assert result[0].name == "Default"

    def test_get_by_id_returns_profile(self, mock_connection):
        """get_by_id should return single TaxProfile."""
        conn, cursor = mock_connection
        cursor.fetchone.return_value = (
            1, "Default", None, Decimal("3.00"), Decimal("3.00"),
            Decimal("3.60"), True, None, None
        )

        repo = TaxRepository(conn)
        result = repo.get_by_id(1)

        assert result is not None
        assert result.id == 1

    def test_get_by_id_returns_none(self, mock_connection):
        """get_by_id should return None if not found."""
        conn, cursor = mock_connection
        cursor.fetchone.return_value = None

        repo = TaxRepository(conn)
        result = repo.get_by_id(999)

        assert result is None

    def test_create_returns_new_profile(self, mock_connection):
        """create should return new TaxProfile with id."""
        conn, cursor = mock_connection
        cursor.fetchone.return_value = (
            2, "New Profile", None, Decimal("2.00"), Decimal("2.00"),
            Decimal("2.50"), False, None, None
        )

        repo = TaxRepository(conn)
        create_data = TaxProfileCreate(
            name="New Profile",
            broker_fee_buy=Decimal("2.00"),
            broker_fee_sell=Decimal("2.00"),
            sales_tax=Decimal("2.50"),
        )
        result = repo.create(create_data)

        assert result.id == 2
        assert result.name == "New Profile"
