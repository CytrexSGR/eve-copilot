"""Tax Invoicing and Payment Matching.

Implements:
- Auto-generation of monthly invoices from mining_tax_ledger
- Payment matching: scan wallet journal for player_donation (ref_type 10)
  matching character + amount
- Partial payments and credit tracking
- Invoice status lifecycle: pending → partial → paid / overdue
"""

import logging
from decimal import Decimal
from typing import Optional

from eve_shared import get_db

logger = logging.getLogger(__name__)


class InvoicingService:
    """Tax invoice generation, payment matching, and compliance tracking."""

    def __init__(self):
        self.db = get_db()

    def generate_invoices(
        self,
        corp_id: int,
        period_start: str,
        period_end: str,
        tax_rate: float = 0.10,
    ) -> list[dict]:
        """Generate monthly invoices from mining_tax_ledger.

        Aggregates all tax entries per character for the given period
        and creates invoice records.
        """
        invoices = []

        with self.db.cursor() as cur:
            # Get tax totals per character for the period
            cur.execute(
                """SELECT mtl.character_id,
                          SUM(mtl.isk_value) as total_mined_value,
                          SUM(mtl.tax_amount) as total_tax
                   FROM mining_tax_ledger mtl
                   JOIN mining_observers mo ON mtl.observer_id = mo.observer_id
                   WHERE mo.corporation_id = %s
                     AND mtl.date >= %s
                     AND mtl.date <= %s
                   GROUP BY mtl.character_id
                   HAVING SUM(mtl.tax_amount) > 0
                   ORDER BY total_tax DESC""",
                (corp_id, period_start, period_end),
            )
            summaries = cur.fetchall()

            for s in summaries:
                char_id = s["character_id"]
                total_mined = Decimal(str(s["total_mined_value"]))
                amount_due = Decimal(str(s["total_tax"]))

                # Check if invoice already exists for this period+character
                cur.execute(
                    """SELECT id FROM tax_invoices
                       WHERE corporation_id = %s AND character_id = %s
                       AND period_start = %s AND period_end = %s""",
                    (corp_id, char_id, period_start, period_end),
                )
                existing = cur.fetchone()
                if existing:
                    # Update existing invoice
                    cur.execute(
                        """UPDATE tax_invoices SET
                               total_mined_value = %s,
                               tax_rate = %s,
                               amount_due = %s,
                               remaining_balance = amount_due - amount_paid,
                               updated_at = NOW()
                           WHERE id = %s""",
                        (total_mined, tax_rate, amount_due, existing["id"]),
                    )
                    invoices.append({"id": existing["id"], "updated": True})
                    continue

                # Check for existing credit from previous overpayments
                cur.execute(
                    """SELECT COALESCE(SUM(credit), 0) as total_credit
                       FROM tax_invoices
                       WHERE corporation_id = %s AND character_id = %s
                       AND credit > 0""",
                    (corp_id, char_id),
                )
                credit_row = cur.fetchone()
                available_credit = Decimal(str(credit_row["total_credit"])) if credit_row else Decimal("0")

                # Apply credit to new invoice
                amount_paid = min(available_credit, amount_due)
                remaining = amount_due - amount_paid
                status = "paid" if remaining <= 0 else "pending"

                # Deduct used credit from previous invoices
                if amount_paid > 0:
                    self._deduct_credit(cur, corp_id, char_id, amount_paid)

                # Create invoice
                cur.execute(
                    """INSERT INTO tax_invoices
                       (corporation_id, character_id, period_start, period_end,
                        total_mined_value, tax_rate, amount_due, amount_paid,
                        remaining_balance, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    (
                        corp_id,
                        char_id,
                        period_start,
                        period_end,
                        total_mined,
                        tax_rate,
                        amount_due,
                        amount_paid,
                        remaining,
                        status,
                    ),
                )
                invoice_id = cur.fetchone()["id"]
                invoices.append({
                    "id": invoice_id,
                    "character_id": char_id,
                    "amount_due": float(amount_due),
                    "credit_applied": float(amount_paid),
                    "remaining": float(remaining),
                    "status": status,
                })

        logger.info(
            "Generated %s invoices for corp %s period %s-%s",
            len(invoices), corp_id, period_start, period_end,
        )
        return invoices

    def _deduct_credit(self, cur, corp_id: int, char_id: int, amount: Decimal):
        """Deduct credit from previous invoices (FIFO order)."""
        cur.execute(
            """SELECT id, credit FROM tax_invoices
               WHERE corporation_id = %s AND character_id = %s AND credit > 0
               ORDER BY period_end ASC""",
            (corp_id, char_id),
        )
        credit_invoices = cur.fetchall()
        remaining = amount
        for ci in credit_invoices:
            if remaining <= 0:
                break
            deduction = min(Decimal(str(ci["credit"])), remaining)
            cur.execute(
                "UPDATE tax_invoices SET credit = credit - %s WHERE id = %s",
                (deduction, ci["id"]),
            )
            remaining -= deduction

    def match_payments(self, corp_id: int) -> dict:
        """Scan wallet journal for payments matching open invoices.

        Matching criteria (per spec Section 4.3):
        1. sender_id matches invoice.character_id
        2. ref_type is 'player_donation' (ref_type 10)
        3. reason contains keywords (mining tax, invoice, etc.)
        4. Fallback: amount matches open invoice balance
        """
        result = {"matched": 0, "total_amount": Decimal("0"), "partial": 0}

        with self.db.cursor() as cur:
            # Get all open invoices for this corp
            cur.execute(
                """SELECT id, character_id, amount_due, amount_paid,
                          remaining_balance
                   FROM tax_invoices
                   WHERE corporation_id = %s AND status IN ('pending', 'partial')
                   ORDER BY period_start ASC""",
                (corp_id,),
            )
            open_invoices = cur.fetchall()

            if not open_invoices:
                return {"matched": 0, "total_amount": 0}

            # Get character IDs with open invoices
            char_ids = list({inv["character_id"] for inv in open_invoices})

            # Find unmatched donations from these characters
            cur.execute(
                """SELECT wj.transaction_id, wj.first_party_id, wj.amount,
                          wj.reason, wj.date
                   FROM corp_wallet_journal wj
                   LEFT JOIN invoice_payment_matches ipm
                       ON wj.transaction_id = ipm.transaction_id
                   WHERE wj.corporation_id = %s
                     AND wj.ref_type = 'player_donation'
                     AND wj.amount > 0
                     AND wj.first_party_id = ANY(%s)
                     AND ipm.id IS NULL
                   ORDER BY wj.date ASC""",
                (corp_id, char_ids),
            )
            donations = cur.fetchall()

            for donation in donations:
                sender_id = donation["first_party_id"]
                amount = Decimal(str(donation["amount"]))
                reason = (donation["reason"] or "").lower()
                tx_id = donation["transaction_id"]

                # Find matching invoice for this sender
                matched_invoice = None
                match_method = "auto"

                # Strategy 1: Reason keyword match
                tax_keywords = ["mining tax", "tax", "invoice", "steuer", "rechnung"]
                has_keyword = any(kw in reason for kw in tax_keywords)

                # Find invoices for this character
                char_invoices = [
                    inv for inv in open_invoices if inv["character_id"] == sender_id
                ]
                if not char_invoices:
                    continue

                if has_keyword:
                    # Match to oldest open invoice
                    matched_invoice = char_invoices[0]
                    match_method = "reason_keyword"
                else:
                    # Strategy 2: Exact or close amount match
                    for inv in char_invoices:
                        remaining = Decimal(str(inv["remaining_balance"]))
                        if remaining > 0 and abs(amount - remaining) < Decimal("1.00"):
                            matched_invoice = inv
                            match_method = "amount_match"
                            break

                    if not matched_invoice:
                        # Strategy 3: Apply to oldest open invoice
                        for inv in char_invoices:
                            if Decimal(str(inv["remaining_balance"])) > 0:
                                matched_invoice = inv
                                match_method = "auto"
                                break

                if not matched_invoice:
                    continue

                # Apply payment
                inv_id = matched_invoice["id"]
                remaining = Decimal(str(matched_invoice["remaining_balance"]))
                payment = min(amount, remaining)
                new_remaining = remaining - payment
                overpayment = max(Decimal("0"), amount - remaining)

                new_paid = Decimal(str(matched_invoice["amount_paid"])) + payment
                new_status = "paid" if new_remaining <= 0 else "partial"

                cur.execute(
                    """UPDATE tax_invoices SET
                           amount_paid = %s,
                           remaining_balance = %s,
                           credit = credit + %s,
                           status = %s,
                           updated_at = NOW()
                       WHERE id = %s""",
                    (new_paid, new_remaining, overpayment, new_status, inv_id),
                )

                # Record the match
                cur.execute(
                    """INSERT INTO invoice_payment_matches
                       (invoice_id, transaction_id, amount, match_method)
                       VALUES (%s, %s, %s, %s)""",
                    (inv_id, tx_id, payment, match_method),
                )

                result["matched"] += 1
                result["total_amount"] += payment
                if new_status == "partial":
                    result["partial"] += 1

                # Update the open_invoices list for subsequent matching
                matched_invoice["amount_paid"] = float(new_paid)
                matched_invoice["remaining_balance"] = float(new_remaining)

        result["total_amount"] = float(result["total_amount"])
        logger.info(
            "Payment matching for corp %s: %s matched, %s ISK",
            corp_id, result["matched"], result["total_amount"],
        )
        return result

    def get_invoice(self, invoice_id: int) -> Optional[dict]:
        """Get a single invoice with payment history."""
        with self.db.cursor() as cur:
            cur.execute(
                """SELECT ti.*, ipm.transaction_id as payment_tx_id,
                          ipm.amount as payment_amount,
                          ipm.matched_at, ipm.match_method
                   FROM tax_invoices ti
                   LEFT JOIN invoice_payment_matches ipm ON ti.id = ipm.invoice_id
                   WHERE ti.id = %s""",
                (invoice_id,),
            )
            rows = cur.fetchall()

        if not rows:
            return None

        invoice = dict(rows[0])
        payments = []
        for row in rows:
            if row["payment_tx_id"]:
                payments.append({
                    "transaction_id": row["payment_tx_id"],
                    "amount": float(row["payment_amount"]),
                    "matched_at": row["matched_at"].isoformat() if row["matched_at"] else None,
                    "match_method": row["match_method"],
                })

        # Clean up invoice dict
        for key in ["payment_tx_id", "payment_amount", "matched_at", "match_method"]:
            invoice.pop(key, None)

        invoice["payments"] = payments
        return invoice

    def list_invoices(
        self,
        corp_id: Optional[int] = None,
        char_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """List invoices with optional filters."""
        conditions = []
        params = []

        if corp_id:
            conditions.append("corporation_id = %s")
            params.append(corp_id)
        if char_id:
            conditions.append("character_id = %s")
            params.append(char_id)
        if status:
            conditions.append("status = %s")
            params.append(status)

        where = " AND ".join(conditions) if conditions else "TRUE"
        params.append(limit)

        with self.db.cursor() as cur:
            cur.execute(
                f"""SELECT id, corporation_id, character_id, period_start,
                           period_end, total_mined_value, tax_rate, amount_due,
                           amount_paid, remaining_balance, credit, status,
                           created_at, updated_at
                    FROM tax_invoices
                    WHERE {where}
                    ORDER BY created_at DESC
                    LIMIT %s""",
                params,
            )
            return [dict(row) for row in cur.fetchall()]
