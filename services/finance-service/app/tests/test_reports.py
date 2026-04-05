"""Tests for financial reports service."""

import os

os.environ.setdefault("EVE_CLIENT_ID", "test_client_id")
os.environ.setdefault("EVE_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("EVE_CALLBACK_URL", "http://localhost/callback")

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app.services.reports import ReportsService
from app.tests.conftest import MultiResultCursor


# ──────────────────────── Fixtures ──────────────────────────


@pytest.fixture
def reports_service():
    """Create a ReportsService with mocked DB."""
    with patch("app.services.reports.get_db") as mock_get_db:
        svc = ReportsService()
        yield svc


# ──────────────────────── PnL days parameter tests ──────────────────────────


class TestPnlReportDaysParameter:
    """Verify that get_pnl_report passes correct days to breakdown sub-calls."""

    def test_pnl_report_passes_correct_days_to_income_breakdown(self, reports_service):
        """get_income_breakdown should receive the actual day count, not 999."""
        period_start = "2026-01-01"
        period_end = "2026-01-31"
        expected_days = (date.fromisoformat(period_end) - date.fromisoformat(period_start)).days

        # Mock the DB cursor for the main PnL queries (2 execute calls)
        cur = MultiResultCursor([
            [{"total_income": Decimal("1000000"), "income_count": 5}],
            [{"total_expenses": Decimal("500000"), "expense_count": 3}],
        ])
        reports_service.db = MagicMock()
        reports_service.db.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        reports_service.db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Mock the sub-calls to capture arguments
        with patch.object(reports_service, "get_income_breakdown", return_value=[]) as mock_income, \
             patch.object(reports_service, "get_expense_summary", return_value=[]) as mock_expense:
            reports_service.get_pnl_report(corp_id=12345, period_start=period_start, period_end=period_end)

            # Income breakdown should get actual days (30), not 999
            mock_income.assert_called_once_with(12345, days=expected_days)
            assert mock_income.call_args.kwargs["days"] == expected_days
            assert mock_income.call_args.kwargs["days"] != 999

    def test_pnl_report_passes_correct_days_to_expense_summary(self, reports_service):
        """get_expense_summary should receive the actual day count, not 999."""
        period_start = "2026-02-01"
        period_end = "2026-02-15"
        expected_days = (date.fromisoformat(period_end) - date.fromisoformat(period_start)).days

        cur = MultiResultCursor([
            [{"total_income": Decimal("2000000"), "income_count": 10}],
            [{"total_expenses": Decimal("800000"), "expense_count": 7}],
        ])
        reports_service.db = MagicMock()
        reports_service.db.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        reports_service.db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(reports_service, "get_income_breakdown", return_value=[]) as mock_income, \
             patch.object(reports_service, "get_expense_summary", return_value=[]) as mock_expense:
            reports_service.get_pnl_report(corp_id=99999, period_start=period_start, period_end=period_end)

            mock_expense.assert_called_once_with(99999, days=expected_days)
            assert mock_expense.call_args.kwargs["days"] == expected_days
            assert mock_expense.call_args.kwargs["days"] != 999

    def test_pnl_report_7_day_range(self, reports_service):
        """A 7-day period should pass days=7 to sub-calls."""
        period_start = "2026-02-10"
        period_end = "2026-02-17"

        cur = MultiResultCursor([
            [{"total_income": Decimal("100"), "income_count": 1}],
            [{"total_expenses": Decimal("50"), "expense_count": 1}],
        ])
        reports_service.db = MagicMock()
        reports_service.db.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        reports_service.db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(reports_service, "get_income_breakdown", return_value=[]) as mock_income, \
             patch.object(reports_service, "get_expense_summary", return_value=[]) as mock_expense:
            reports_service.get_pnl_report(corp_id=1, period_start=period_start, period_end=period_end)

            assert mock_income.call_args.kwargs["days"] == 7
            assert mock_expense.call_args.kwargs["days"] == 7

    def test_pnl_report_single_day_range(self, reports_service):
        """A same-day range should pass days=0 to sub-calls."""
        period_start = "2026-02-19"
        period_end = "2026-02-19"

        cur = MultiResultCursor([
            [{"total_income": Decimal("0"), "income_count": 0}],
            [{"total_expenses": Decimal("0"), "expense_count": 0}],
        ])
        reports_service.db = MagicMock()
        reports_service.db.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        reports_service.db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(reports_service, "get_income_breakdown", return_value=[]) as mock_income, \
             patch.object(reports_service, "get_expense_summary", return_value=[]) as mock_expense:
            reports_service.get_pnl_report(corp_id=1, period_start=period_start, period_end=period_end)

            assert mock_income.call_args.kwargs["days"] == 0
            assert mock_expense.call_args.kwargs["days"] == 0


# ──────────────────────── PnL report output structure ──────────────────────────


class TestPnlReportOutput:
    """Verify the structure and values of get_pnl_report output."""

    def test_pnl_report_returns_correct_net_profit(self, reports_service):
        """Net profit = total_income - total_expenses."""
        cur = MultiResultCursor([
            [{"total_income": Decimal("5000000"), "income_count": 20}],
            [{"total_expenses": Decimal("2000000"), "expense_count": 10}],
        ])
        reports_service.db = MagicMock()
        reports_service.db.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        reports_service.db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(reports_service, "get_income_breakdown", return_value=[]), \
             patch.object(reports_service, "get_expense_summary", return_value=[]):
            result = reports_service.get_pnl_report(
                corp_id=1, period_start="2026-01-01", period_end="2026-01-31"
            )

        assert result["total_income"] == 5000000.0
        assert result["total_expenses"] == 2000000.0
        assert result["net_profit"] == 3000000.0
        assert result["income_transactions"] == 20
        assert result["expense_transactions"] == 10

    def test_pnl_report_includes_period_and_corp(self, reports_service):
        """Report includes the requested period and corporation ID."""
        cur = MultiResultCursor([
            [{"total_income": Decimal("0"), "income_count": 0}],
            [{"total_expenses": Decimal("0"), "expense_count": 0}],
        ])
        reports_service.db = MagicMock()
        reports_service.db.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        reports_service.db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(reports_service, "get_income_breakdown", return_value=[]), \
             patch.object(reports_service, "get_expense_summary", return_value=[]):
            result = reports_service.get_pnl_report(
                corp_id=98378388, period_start="2026-02-01", period_end="2026-02-15"
            )

        assert result["corporation_id"] == 98378388
        assert result["period_start"] == "2026-02-01"
        assert result["period_end"] == "2026-02-15"


# ──────────────────────── Income breakdown tests ──────────────────────────


class TestIncomeBreakdown:
    """Test get_income_breakdown grouping and sorting."""

    def test_income_grouped_by_category(self, reports_service):
        """Income rows are grouped by category."""
        rows = [
            {"ref_type": "bounty_prize", "category": "ratting", "label_de": "Kopfgeld",
             "transaction_count": 10, "total_amount": Decimal("5000000")},
            {"ref_type": "bounty_prizes", "category": "ratting", "label_de": "Kopfgelder",
             "transaction_count": 5, "total_amount": Decimal("3000000")},
            {"ref_type": "market_transaction", "category": "market", "label_de": "Markt",
             "transaction_count": 3, "total_amount": Decimal("1000000")},
        ]
        cur = MagicMock()
        cur.fetchall.return_value = rows
        reports_service.db = MagicMock()
        reports_service.db.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        reports_service.db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = reports_service.get_income_breakdown(corp_id=1, days=30)

        assert len(result) == 2
        # Sorted by total_amount desc
        assert result[0]["category"] == "ratting"
        assert result[0]["total_amount"] == Decimal("8000000")
        assert result[0]["transaction_count"] == 15
        assert result[1]["category"] == "market"
        assert result[1]["total_amount"] == Decimal("1000000")

    def test_income_null_category_becomes_other(self, reports_service):
        """Rows with NULL category are grouped under 'other'."""
        rows = [
            {"ref_type": "unknown_type", "category": None, "label_de": None,
             "transaction_count": 1, "total_amount": Decimal("100")},
        ]
        cur = MagicMock()
        cur.fetchall.return_value = rows
        reports_service.db = MagicMock()
        reports_service.db.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        reports_service.db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = reports_service.get_income_breakdown(corp_id=1, days=7)

        assert len(result) == 1
        assert result[0]["category"] == "other"


# ──────────────────────── Expense summary tests ──────────────────────────


class TestExpenseSummary:
    """Test get_expense_summary formatting."""

    def test_expense_summary_formats_output(self, reports_service):
        """Expense rows are formatted with proper field names and types."""
        rows = [
            {"division_id": 1, "division_name": "Master Wallet",
             "transaction_count": 50, "total_amount": Decimal("10000000.50")},
            {"division_id": 2, "division_name": None,
             "transaction_count": 5, "total_amount": Decimal("500000")},
        ]
        cur = MagicMock()
        cur.fetchall.return_value = rows
        reports_service.db = MagicMock()
        reports_service.db.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        reports_service.db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = reports_service.get_expense_summary(corp_id=1, days=30)

        assert len(result) == 2
        assert result[0]["division_name"] == "Master Wallet"
        assert result[0]["total_amount"] == 10000000.50
        assert isinstance(result[0]["total_amount"], float)
        # None division_name falls back to "Division X"
        assert result[1]["division_name"] == "Division 2"
