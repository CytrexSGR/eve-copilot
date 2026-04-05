"""Corporation data models."""
from typing import Optional, List
from pydantic import BaseModel


class CorporationInfo(BaseModel):
    """Corporation public information."""
    corporation_id: int
    name: str
    ticker: str = ""
    member_count: int = 0
    alliance_id: Optional[int] = None
    ceo_id: Optional[int] = None
    creator_id: Optional[int] = None
    date_founded: Optional[str] = None
    description: Optional[str] = None
    home_station_id: Optional[int] = None
    shares: int = 0
    tax_rate: float = 0.0
    url: Optional[str] = None


class CorporationWalletDivision(BaseModel):
    """Corporation wallet division."""
    division: int
    balance: float = 0.0


class CorporationWallet(BaseModel):
    """Corporation wallets."""
    corporation_id: int
    corporation_name: str = ""
    divisions: List[CorporationWalletDivision] = []
    total_balance: float = 0.0
    formatted_total: str = ""


class CorpMarketOrder(BaseModel):
    """Corporation market order."""
    order_id: int
    type_id: int
    type_name: str = "Unknown"
    is_buy_order: bool = False
    price: float = 0.0
    volume_total: int = 0
    volume_remain: int = 0
    location_id: int = 0
    location_name: str = "Unknown"
    region_id: int = 0
    issued: Optional[str] = None
    duration: int = 0
    issued_by: int = 0
    wallet_division: int = 1


class CorpMarketOrderList(BaseModel):
    """Corporation market orders."""
    corporation_id: int
    orders: List[CorpMarketOrder] = []


class CorpTransaction(BaseModel):
    """Corporation wallet transaction."""
    transaction_id: int
    date: str
    type_id: int
    type_name: str = "Unknown"
    quantity: int = 0
    unit_price: float = 0.0
    is_buy: bool = False
    location_id: int = 0
    location_name: str = "Unknown"
    client_id: int = 0
    wallet_division: int = 1


class CorpTransactions(BaseModel):
    """Corporation transactions."""
    corporation_id: int
    transactions: List[CorpTransaction] = []
