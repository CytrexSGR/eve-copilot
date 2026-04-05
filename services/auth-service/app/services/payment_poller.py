"""
Wallet Journal Payment Poller.

Polls holding character wallet journal via ESI,
matches incoming ISK transfers against pending payment codes,
and activates subscriptions on match.
"""
import re
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

CODE_PATTERN = re.compile(r"PAY-([A-Z0-9]{5})", re.IGNORECASE)


def extract_reference_code(text: Optional[str]) -> Optional[str]:
    """Extract PAY-XXXXX code from wallet journal reason field."""
    if not text:
        return None
    match = CODE_PATTERN.search(text)
    if match:
        return match.group(0).upper()
    return None


def is_player_donation(entry: Dict[str, Any]) -> bool:
    """Check if wallet journal entry is an incoming player donation."""
    return (
        entry.get("ref_type") == "player_donation"
        and (entry.get("amount") or 0) > 0
    )


def match_payment(
    entry: Dict[str, Any],
    pending_payments: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Match a wallet journal entry to a pending payment.

    Criteria:
    - Reference code in journal "reason" field
    - Amount >= expected (overpayment OK, underpayment rejected)
    """
    code = extract_reference_code(entry.get("reason"))
    if not code:
        return None

    amount = entry.get("amount", 0)

    for pending in pending_payments:
        if pending["reference_code"] == code and amount >= pending["amount"]:
            return pending

    return None
