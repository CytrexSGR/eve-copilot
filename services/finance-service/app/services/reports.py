"""Financial Reports - Income, expenses, P&L summaries.

Implements:
- Income breakdown by ref_type category
- Expense tracking by division
- Monthly P&L: Revenue - expenses per division
- Ratting tax audit
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from eve_shared import get_db

logger = logging.getLogger(__name__)

# Categories for income/expense classification
INCOME_CATEGORIES = {
    "ratting": ["bounty_prize", "bounty_prizes", "agent_mission_reward",
                "mission_reward", "mission_time_bonus_reward"],
    "market": ["player_trading", "market_transaction"],
    "pi": ["planetary_import_tax", "planetary_export_tax"],
    "corp_tax": ["bounty_prizes", "reprocessing_tax"],
    "transfer": ["player_donation"],
    "industry": ["manufacturing"],
}

EXPENSE_REF_TYPES = {
    "brokers_fee", "transaction_tax", "corporation_account_withdrawal",
    "structure_gate_jump",
}


class ReportsService:
    """Financial reporting service."""

    def __init__(self):
        self.db = get_db()

    def get_income_breakdown(
        self, corp_id: int, days: int = 30, division_id: int = 1
    ) -> list[dict]:
        """Get income breakdown by ref_type category."""
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT ref_type,
                          rt.category,
                          rt.label_de,
                          COUNT(*) as transaction_count,
                          SUM(amount) as total_amount
                   FROM corp_wallet_journal cwj
                   LEFT JOIN ref_types rt ON cwj.ref_type = rt.name
                   WHERE cwj.corporation_id = %s
                     AND cwj.division_id = %s
                     AND cwj.amount > 0
                     AND cwj.date >= CURRENT_DATE - INTERVAL '1 day' * %s
                   GROUP BY ref_type, rt.category, rt.label_de
                   ORDER BY total_amount DESC""",
                (corp_id, division_id, days),
            )
            rows = cur.fetchall()

        # Group by category
        category_totals: dict = {}
        for row in rows:
            category = row["category"] or "other"
            if category not in category_totals:
                category_totals[category] = {
                    "category": category,
                    "ref_types": [],
                    "total_amount": Decimal("0"),
                    "transaction_count": 0,
                }
            category_totals[category]["ref_types"].append(row["ref_type"])
            category_totals[category]["total_amount"] += row["total_amount"] or 0
            category_totals[category]["transaction_count"] += row["transaction_count"]

        return sorted(
            category_totals.values(),
            key=lambda x: x["total_amount"],
            reverse=True,
        )

    def get_expense_summary(self, corp_id: int, days: int = 30) -> list[dict]:
        """Get expense summary by division."""
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT cwj.division_id,
                          wd.name as division_name,
                          COUNT(*) as transaction_count,
                          SUM(ABS(cwj.amount)) as total_amount
                   FROM corp_wallet_journal cwj
                   LEFT JOIN wallet_divisions wd
                       ON cwj.corporation_id = wd.corporation_id
                       AND cwj.division_id = wd.division_id
                   WHERE cwj.corporation_id = %s
                     AND cwj.amount < 0
                     AND cwj.date >= CURRENT_DATE - INTERVAL '1 day' * %s
                   GROUP BY cwj.division_id, wd.name
                   ORDER BY total_amount DESC""",
                (corp_id, days),
            )
            return [
                {
                    "division_id": row["division_id"],
                    "division_name": row["division_name"] or f"Division {row['division_id']}",
                    "total_amount": float(row["total_amount"]),
                    "transaction_count": row["transaction_count"],
                }
                for row in cur.fetchall()
            ]

    def get_pnl_report(
        self, corp_id: int, period_start: str, period_end: str
    ) -> dict:
        """Get Profit & Loss report for a period."""
        with self.db.cursor() as cur:
            # Total income (positive amounts)
            cur.execute(
                """SELECT COALESCE(SUM(amount), 0) as total_income,
                          COUNT(*) as income_count
                   FROM corp_wallet_journal
                   WHERE corporation_id = %s
                     AND amount > 0
                     AND date >= %s AND date <= %s""",
                (corp_id, period_start, period_end),
            )
            income = cur.fetchone()

            # Total expenses (negative amounts)
            cur.execute(
                """SELECT COALESCE(SUM(ABS(amount)), 0) as total_expenses,
                          COUNT(*) as expense_count
                   FROM corp_wallet_journal
                   WHERE corporation_id = %s
                     AND amount < 0
                     AND date >= %s AND date <= %s""",
                (corp_id, period_start, period_end),
            )
            expenses = cur.fetchone()

        total_income = Decimal(str(income["total_income"]))
        total_expenses = Decimal(str(expenses["total_expenses"]))

        # Calculate actual days for breakdown sub-calls
        days = (date.fromisoformat(period_end) - date.fromisoformat(period_start)).days

        # Get breakdowns
        income_breakdown = self.get_income_breakdown(corp_id, days=days)
        expense_breakdown = self.get_expense_summary(corp_id, days=days)

        return {
            "corporation_id": corp_id,
            "period_start": period_start,
            "period_end": period_end,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_profit": float(total_income - total_expenses),
            "income_transactions": income["income_count"],
            "expense_transactions": expenses["expense_count"],
            "income_breakdown": income_breakdown,
            "expense_breakdown": expense_breakdown,
        }

    def get_ratting_tax_audit(
        self, corp_id: int, days: int = 30
    ) -> list[dict]:
        """Compare bounty_prizes (corp tax income) with member ratting activity.

        Identifies potential tax evasion by comparing corp tax income (ref_type 85)
        with expected income based on ratting activity.
        """
        with self.db.cursor() as cur:
            # Get corp bounty income per second_party_id (the ratting character)
            cur.execute(
                """SELECT second_party_id as character_id,
                          SUM(amount) as corp_tax_received,
                          COUNT(*) as bounty_count
                   FROM corp_wallet_journal
                   WHERE corporation_id = %s
                     AND ref_type = 'bounty_prizes'
                     AND date >= CURRENT_DATE - INTERVAL '1 day' * %s
                   GROUP BY second_party_id
                   ORDER BY corp_tax_received DESC""",
                (corp_id, days),
            )
            return [dict(row) for row in cur.fetchall()]
