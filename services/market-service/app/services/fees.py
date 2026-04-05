"""EVE Online trading fee calculations.

Exact formulas per CCP game mechanics:
- Broker Fee: 3.0% - (0.3% * Broker Relations level), min 1.0% at NPC stations
- Sales Tax: 8.0% * (1 - 0.11 * Accounting level)

Skill type IDs (from SDE invTypes):
- Broker Relations: 3446
- Advanced Broker Relations: 16597 (relist discount only)
- Accounting: 16622
"""

SKILL_BROKER_RELATIONS = 3446
SKILL_ACCOUNTING = 16622
SKILL_ADVANCED_BROKER_RELATIONS = 16597

BASE_BROKER_FEE_PCT = 3.0
BROKER_REDUCTION_PER_LEVEL = 0.3
FACTION_STANDING_FACTOR = 0.03
CORP_STANDING_FACTOR = 0.02
MIN_BROKER_FEE_PCT = 1.0

BASE_SALES_TAX_PCT = 8.0
ACCOUNTING_REDUCTION_PER_LEVEL = 0.11

DEFAULT_BROKER_RELATIONS = 5
DEFAULT_ACCOUNTING = 5


def broker_fee_rate(
    broker_relations: int = DEFAULT_BROKER_RELATIONS,
    faction_standing: float = 0.0,
    corp_standing: float = 0.0,
) -> float:
    """Calculate broker fee percentage.

    Formula: max(1.0, 3.0 - 0.3 * skill - 0.03 * faction - 0.02 * corp)

    Args:
        broker_relations: Broker Relations skill level (0-5).
        faction_standing: Faction standing with the station owner (-10 to +10).
        corp_standing: Corporation standing with the station owner (-10 to +10).

    Returns:
        Broker fee as a percentage (e.g. 1.5 means 1.5%).
    """
    rate = (
        BASE_BROKER_FEE_PCT
        - BROKER_REDUCTION_PER_LEVEL * broker_relations
        - FACTION_STANDING_FACTOR * faction_standing
        - CORP_STANDING_FACTOR * corp_standing
    )
    return max(MIN_BROKER_FEE_PCT, rate)


def sales_tax_rate(accounting: int = DEFAULT_ACCOUNTING) -> float:
    """Calculate sales tax percentage.

    Formula: 8.0 * (1 - 0.11 * skill)

    Args:
        accounting: Accounting skill level (0-5).

    Returns:
        Sales tax as a percentage (e.g. 3.6 means 3.6%).
    """
    return BASE_SALES_TAX_PCT * (1.0 - ACCOUNTING_REDUCTION_PER_LEVEL * accounting)


def calculate_trade_fees(
    buy_price: float,
    sell_price: float,
    broker_relations: int = DEFAULT_BROKER_RELATIONS,
    accounting: int = DEFAULT_ACCOUNTING,
) -> dict:
    """Calculate all trading fees for a buy+sell transaction in ISK.

    The broker fee is paid twice: once when placing the buy order and once
    when placing the sell order.  Sales tax is paid only on the sell.

    Args:
        buy_price: Price per unit when buying.
        sell_price: Price per unit when selling.
        broker_relations: Broker Relations skill level (0-5).
        accounting: Accounting skill level (0-5).

    Returns:
        Dict with broker_fee_buy, broker_fee_sell, sales_tax, total_fees,
        broker_fee_pct, and sales_tax_pct.
    """
    bf_pct = broker_fee_rate(broker_relations)
    st_pct = sales_tax_rate(accounting)

    broker_fee_buy = buy_price * bf_pct / 100.0
    broker_fee_sell = sell_price * bf_pct / 100.0
    st = sell_price * st_pct / 100.0

    return {
        "broker_fee_buy": broker_fee_buy,
        "broker_fee_sell": broker_fee_sell,
        "sales_tax": st,
        "total_fees": broker_fee_buy + broker_fee_sell + st,
        "broker_fee_pct": bf_pct,
        "sales_tax_pct": st_pct,
    }


def net_profit_per_unit(
    buy_price: float,
    sell_price: float,
    broker_relations: int = DEFAULT_BROKER_RELATIONS,
    accounting: int = DEFAULT_ACCOUNTING,
) -> dict:
    """Calculate net profit per unit after all trading fees.

    Args:
        buy_price: Price per unit when buying.
        sell_price: Price per unit when selling.
        broker_relations: Broker Relations skill level (0-5).
        accounting: Accounting skill level (0-5).

    Returns:
        Dict with gross_profit, total_fees, net_profit, gross_margin_pct,
        net_margin_pct, and is_profitable.
    """
    fees = calculate_trade_fees(buy_price, sell_price, broker_relations, accounting)
    gross_profit = sell_price - buy_price
    net_profit = gross_profit - fees["total_fees"]

    if sell_price > 0:
        gross_margin_pct = (gross_profit / sell_price) * 100.0
        net_margin_pct = (net_profit / sell_price) * 100.0
    else:
        gross_margin_pct = 0.0
        net_margin_pct = 0.0

    return {
        "gross_profit": gross_profit,
        "total_fees": fees["total_fees"],
        "net_profit": net_profit,
        "gross_margin_pct": gross_margin_pct,
        "net_margin_pct": net_margin_pct,
        "is_profitable": net_profit > 0,
    }
