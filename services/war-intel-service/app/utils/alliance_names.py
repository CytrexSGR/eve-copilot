"""Alliance name resolution from alliance_name_cache with ESI fallback."""

from typing import Dict, List, Tuple


def get_alliance_name(cur, alliance_id: int) -> str:
    """Fetch a single alliance name. Returns 'Alliance {id}' if not found."""
    cur.execute(
        "SELECT alliance_name FROM alliance_name_cache WHERE alliance_id = %s",
        (alliance_id,)
    )
    row = cur.fetchone()
    if row is None:
        return f"Alliance {alliance_id}"
    return row["alliance_name"] if isinstance(row, dict) else row[0]


def batch_get_alliance_names(cur, alliance_ids: List[int]) -> Dict[int, str]:
    """Batch fetch alliance names. Returns {alliance_id: name} dict."""
    if not alliance_ids:
        return {}
    cur.execute(
        "SELECT alliance_id, alliance_name FROM alliance_name_cache WHERE alliance_id = ANY(%s)",
        (list(alliance_ids),)
    )
    rows = cur.fetchall()
    if rows and isinstance(rows[0], dict):
        return {r["alliance_id"]: r["alliance_name"] for r in rows}
    return {r[0]: r[1] for r in rows}


def batch_get_alliance_info(cur, alliance_ids: List[int]) -> Tuple[Dict[int, str], Dict[int, str]]:
    """Batch fetch alliance names and tickers.

    Returns:
        (name_map, ticker_map) — both {alliance_id: str}
    """
    if not alliance_ids:
        return {}, {}
    cur.execute(
        "SELECT alliance_id, alliance_name, ticker FROM alliance_name_cache WHERE alliance_id = ANY(%s)",
        (list(alliance_ids),)
    )
    rows = cur.fetchall()
    name_map = {}
    ticker_map = {}
    for r in rows:
        if isinstance(r, dict):
            name_map[r["alliance_id"]] = r["alliance_name"]
            ticker_map[r["alliance_id"]] = r.get("ticker", "")
        else:
            name_map[r[0]] = r[1]
            ticker_map[r[0]] = r[2] if len(r) > 2 else ""
    return name_map, ticker_map
