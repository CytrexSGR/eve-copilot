"""Finance Service Pydantic schemas."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# --- Wallet Journal ---

class WalletJournalEntry(BaseModel):
    """Corporation wallet journal entry."""
    transaction_id: int
    corporation_id: int
    division_id: int = 1
    date: datetime
    ref_type: str
    ref_type_label: Optional[str] = None
    first_party_id: Optional[int] = None
    second_party_id: Optional[int] = None
    amount: Decimal = Decimal("0.00")
    balance: Decimal = Decimal("0.00")
    reason: Optional[str] = None
    extra_info: Dict[str, Any] = Field(default_factory=dict)


class WalletSyncRequest(BaseModel):
    """Request to sync corp wallet journal."""
    corporation_id: int
    character_id: int  # Character with director role for ESI auth
    division_id: int = Field(default=1, ge=1, le=7)
    all_divisions: bool = False  # Sync all 7 divisions at once


class WalletSyncResult(BaseModel):
    """Result of wallet sync operation."""
    corporation_id: int
    division_id: int
    new_entries: int = 0
    gaps_filled: int = 0
    pages_fetched: int = 0


# --- Ref Types ---

class RefType(BaseModel):
    """Wallet journal reference type mapping."""
    ref_type_id: int
    name: str
    label_de: Optional[str] = None
    category: Optional[str] = None


# --- Wallet Divisions ---

class WalletDivision(BaseModel):
    """Corporation wallet division."""
    corporation_id: int
    division_id: int
    name: str


# --- Mining Observer ---

class MiningObserver(BaseModel):
    """Mining observer structure."""
    observer_id: int
    observer_type: str = "structure"
    last_updated: Optional[datetime] = None


class MiningLedgerEntry(BaseModel):
    """Mining observer ledger entry."""
    observer_id: int
    character_id: int
    character_name: Optional[str] = None
    type_id: int
    type_name: Optional[str] = None
    last_updated: date
    quantity: int
    delta_quantity: int = 0
    isk_value: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")


class MiningTaxSummary(BaseModel):
    """Mining tax summary per character."""
    character_id: int
    character_name: Optional[str] = None
    total_mined_quantity: int = 0
    total_isk_value: Decimal = Decimal("0.00")
    total_tax: Decimal = Decimal("0.00")
    ore_breakdown: List[Dict[str, Any]] = Field(default_factory=list)


# --- Tax Invoices ---

class TaxInvoice(BaseModel):
    """Mining tax invoice."""
    id: Optional[int] = None
    character_id: int
    character_name: Optional[str] = None
    period_start: date
    period_end: date
    total_mined_value: Decimal = Decimal("0.00")
    tax_rate: Decimal = Decimal("0.10")
    amount_due: Decimal = Decimal("0.00")
    amount_paid: Decimal = Decimal("0.00")
    remaining_balance: Decimal = Decimal("0.00")
    status: str = "pending"  # pending, partial, paid, overdue
    created_at: Optional[datetime] = None


class InvoiceGenerateRequest(BaseModel):
    """Request to generate invoices for a period."""
    corporation_id: int
    period_start: date
    period_end: date
    tax_rate: Decimal = Decimal("0.10")


# --- Financial Reports ---

class IncomeBreakdown(BaseModel):
    """Income breakdown by category."""
    category: str
    ref_types: List[str] = Field(default_factory=list)
    total_amount: Decimal = Decimal("0.00")
    transaction_count: int = 0


class ExpenseSummary(BaseModel):
    """Expense summary by division."""
    division_id: int
    division_name: Optional[str] = None
    total_amount: Decimal = Decimal("0.00")
    transaction_count: int = 0


class PnlReport(BaseModel):
    """Monthly Profit & Loss report."""
    corporation_id: int
    period_start: date
    period_end: date
    total_income: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_profit: Decimal = Decimal("0.00")
    income_breakdown: List[IncomeBreakdown] = Field(default_factory=list)
    expense_breakdown: List[ExpenseSummary] = Field(default_factory=list)


# --- Fleet Doctrines ---

class DoctrineSlotItem(BaseModel):
    """Single module in a doctrine slot."""
    type_id: int
    type_name: Optional[str] = None
    quantity: int = 1


class DoctrineFitting(BaseModel):
    """Normalized fitting structure for a doctrine."""
    high: List[DoctrineSlotItem] = Field(default_factory=list)
    med: List[DoctrineSlotItem] = Field(default_factory=list)
    low: List[DoctrineSlotItem] = Field(default_factory=list)
    rig: List[DoctrineSlotItem] = Field(default_factory=list)
    drones: List[DoctrineSlotItem] = Field(default_factory=list)


class DoctrineCreate(BaseModel):
    """Request to create a new doctrine."""
    corporation_id: int
    name: str = Field(min_length=1, max_length=200)
    ship_type_id: int
    fitting: DoctrineFitting
    base_payout: Optional[Decimal] = None
    created_by: Optional[int] = None
    category: Optional[str] = "general"


class DoctrineUpdate(BaseModel):
    """Request to update an existing doctrine."""
    name: Optional[str] = None
    fitting: Optional[DoctrineFitting] = None
    base_payout: Optional[Decimal] = None
    is_active: Optional[bool] = None


class DoctrineImportEft(BaseModel):
    """Import a doctrine from EFT text format."""
    corporation_id: int
    eft_text: str = Field(min_length=10)
    base_payout: Optional[Decimal] = None
    created_by: Optional[int] = None


class DoctrineImportDna(BaseModel):
    """Import a doctrine from DNA string format."""
    corporation_id: int
    name: str = Field(min_length=1, max_length=200)
    dna_string: str = Field(min_length=5)
    base_payout: Optional[Decimal] = None
    created_by: Optional[int] = None


class DoctrineResponse(BaseModel):
    """Doctrine response model."""
    id: int
    corporation_id: int
    name: str
    ship_type_id: int
    ship_name: Optional[str] = None
    fitting_json: DoctrineFitting
    is_active: bool = True
    base_payout: Optional[Decimal] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    category: Optional[str] = "general"


class DoctrineCloneRequest(BaseModel):
    """Request to clone an existing doctrine."""
    new_name: str
    category: Optional[str] = None


class DoctrineChangelogEntry(BaseModel):
    """Single changelog entry for a doctrine."""
    id: int
    doctrine_id: int
    actor_character_id: int
    actor_name: str
    action: str
    changes: dict
    created_at: str


class DoctrineAutoPriceResponse(BaseModel):
    """Auto-calculated price breakdown for a doctrine fitting."""
    doctrine_id: int
    total_price: float
    item_prices: dict
    price_source: str
    priced_at: str


# --- SRP Requests ---

class SrpSubmitRequest(BaseModel):
    """Submit an SRP request."""
    corporation_id: int
    character_id: int
    character_name: Optional[str] = None
    killmail_id: int
    killmail_hash: str = Field(min_length=20, max_length=64)
    doctrine_id: Optional[int] = None  # Auto-detected if omitted


class SrpReviewRequest(BaseModel):
    """Approve or reject an SRP request."""
    status: str = Field(pattern="^(approved|rejected)$")
    reviewed_by: int
    review_note: Optional[str] = None


class SrpResponse(BaseModel):
    """SRP request response."""
    id: int
    corporation_id: int
    character_id: int
    character_name: Optional[str] = None
    killmail_id: int
    killmail_hash: str
    ship_type_id: Optional[int] = None
    ship_name: Optional[str] = None
    doctrine_id: Optional[int] = None
    doctrine_name: Optional[str] = None
    payout_amount: Decimal = Decimal("0.00")
    fitting_value: Decimal = Decimal("0.00")
    insurance_payout: Decimal = Decimal("0.00")
    status: str = "pending"
    match_result: Dict[str, Any] = Field(default_factory=dict)
    match_score: Decimal = Decimal("0.00")
    submitted_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    paid_at: Optional[datetime] = None
    compliance_score: Optional[Decimal] = None
    scoring_method: str = "fuzzy"


class SrpConfigUpdate(BaseModel):
    """Update SRP configuration."""
    pricing_mode: Optional[str] = Field(None, pattern="^(jita_buy|jita_sell|jita_split)$")
    default_insurance_level: Optional[str] = Field(
        None,
        pattern="^(none|basic|standard|bronze|silver|gold|platinum)$"
    )
    auto_approve_threshold: Optional[Decimal] = Field(None, ge=0, le=1)
    max_payout: Optional[Decimal] = None


class DoctrineImportFittingItem(BaseModel):
    """Single item from a fitting (ESI or custom)."""
    type_id: int
    flag: int = 0
    quantity: int = 1


class DoctrineImportFitting(BaseModel):
    """Import a doctrine from a fitting's items (ESI or custom fitting)."""
    name: str = Field(min_length=1, max_length=200)
    ship_type_id: int
    items: List[DoctrineImportFittingItem]
    base_payout: Optional[Decimal] = None
    category: Optional[str] = "general"
    corporation_id: int
    created_by: Optional[int] = None
