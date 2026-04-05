"""Market manipulation scanner using Z-score analysis.

Detects anomalous price/volume movements for critical war-economy items
across trade hub regions.
"""

import logging
import math
from datetime import datetime, timezone

from eve_shared.constants import REGION_NAMES, TRADE_HUB_REGIONS

logger = logging.getLogger(__name__)

# Trade hub region IDs to scan
MONITORED_REGIONS = list(TRADE_HUB_REGIONS.values())

# Critical items to monitor for manipulation
CRITICAL_ITEMS = {
    "Interdiction Nullifier": 37615,
    "Nanite Repair Paste": 28668,
    "Warp Disrupt Probe": 23265,
    "Mobile Cyno Inhibitor": 36912,
    "Strontium Clathrates": 16275,
}

# Z-score threshold for alerting
Z_SCORE_THRESHOLD = 2.5


def calculate_z_score(value: float, mean: float, stddev: float) -> float:
    """Calculate absolute Z-score."""
    if stddev == 0:
        return 0.0
    return abs((value - mean) / stddev)


def classify_severity(z_score: float) -> str:
    """Classify severity from Z-score."""
    if z_score >= 4.0:
        return "confirmed"
    elif z_score >= 3.0:
        return "probable"
    elif z_score >= Z_SCORE_THRESHOLD:
        return "suspicious"
    return "normal"


def determine_manipulation_type(price_change: float, volume_change: float) -> str:
    """Determine what kind of manipulation is occurring."""
    price_significant = abs(price_change) > 50
    volume_significant = abs(volume_change) > 50

    if price_significant and volume_significant:
        return "combined"
    elif price_significant:
        return "price_spike"
    return "volume_anomaly"


def fetch_baselines(db, region_id: int, type_ids: list, days: int = 30) -> dict:
    """Fetch baseline stats from war_economy_price_history."""
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    type_id,
                    AVG(lowest_sell) as avg_price,
                    COALESCE(STDDEV(lowest_sell), 0) as price_stddev,
                    AVG(COALESCE(sell_volume, 0) + COALESCE(buy_volume, 0)) as avg_volume,
                    COALESCE(STDDEV(COALESCE(sell_volume, 0) + COALESCE(buy_volume, 0)), 0) as volume_stddev,
                    COUNT(*) as sample_count
                FROM war_economy_price_history
                WHERE region_id = %s
                  AND type_id = ANY(%s)
                  AND snapshot_time >= NOW() - INTERVAL '%s days'
                GROUP BY type_id
                HAVING COUNT(*) >= 3
                """,
                (region_id, type_ids, days),
            )
            results = {}
            for row in cur.fetchall():
                type_id, avg_price, price_std, avg_vol, vol_std, count = row
                avg_price = float(avg_price) if avg_price else 0
                price_std = float(price_std) if price_std else 0
                avg_vol = float(avg_vol) if avg_vol else 0
                vol_std = float(vol_std) if vol_std else 0

                # Min stddev is 1% of mean to avoid zero-division
                if price_std < avg_price * 0.01:
                    price_std = max(avg_price * 0.01, 1.0)
                if vol_std < avg_vol * 0.01:
                    vol_std = max(avg_vol * 0.01, 1.0)

                results[type_id] = {
                    "avg_price": avg_price,
                    "price_stddev": price_std,
                    "avg_volume": avg_vol,
                    "volume_stddev": vol_std,
                    "sample_count": count,
                }
            return results


def fetch_current_prices(db, region_id: int, type_ids: list) -> dict:
    """Fetch latest prices from market_prices."""
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT type_id,
                       COALESCE(lowest_sell, 0) as price,
                       COALESCE(sell_volume, 0) + COALESCE(buy_volume, 0) as volume
                FROM market_prices
                WHERE region_id = %s AND type_id = ANY(%s)
                """,
                (region_id, type_ids),
            )
            return {
                row[0]: {"price": float(row[1]), "volume": row[2]}
                for row in cur.fetchall()
            }


def store_alerts(db, alerts: list):
    """Persist manipulation alerts to database."""
    if not alerts:
        return
    with db.connection() as conn:
        with conn.cursor() as cur:
            for a in alerts:
                cur.execute(
                    """
                    INSERT INTO war_economy_manipulation_alerts (
                        type_id, type_name, region_id, region_name,
                        current_price, baseline_price, price_change_percent,
                        current_volume, baseline_volume, volume_change_percent,
                        z_score, severity, manipulation_type
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        a["type_id"], a["type_name"], a["region_id"], a["region_name"],
                        a["current_price"], a["baseline_price"], a["price_change_percent"],
                        a["current_volume"], a["baseline_volume"], a["volume_change_percent"],
                        a["z_score"], a["severity"], a["manipulation_type"],
                    ),
                )
            conn.commit()


def scan_manipulation(db) -> dict:
    """Scan all monitored regions for market manipulation.

    Args:
        db: eve_shared DatabasePool instance (from request.app.state.db)

    Returns:
        dict with status, job name and alert counts.
    """
    start = datetime.now(timezone.utc)
    type_ids = list(CRITICAL_ITEMS.values())
    all_alerts = []

    for region_id in MONITORED_REGIONS:
        baselines = fetch_baselines(db, region_id, type_ids)
        current = fetch_current_prices(db, region_id, type_ids)
        region_name = REGION_NAMES.get(region_id, f"Region {region_id}")

        for type_name, type_id in CRITICAL_ITEMS.items():
            if type_id not in baselines or type_id not in current:
                continue

            bl = baselines[type_id]
            cu = current[type_id]

            price_z = calculate_z_score(cu["price"], bl["avg_price"], bl["price_stddev"])
            volume_z = calculate_z_score(cu["volume"], bl["avg_volume"], bl["volume_stddev"])
            combined_z = math.sqrt(price_z ** 2 + volume_z ** 2)

            if combined_z >= Z_SCORE_THRESHOLD:
                price_chg = ((cu["price"] - bl["avg_price"]) / bl["avg_price"]) * 100 if bl["avg_price"] else 0
                vol_chg = ((cu["volume"] - bl["avg_volume"]) / bl["avg_volume"]) * 100 if bl["avg_volume"] else 0

                all_alerts.append({
                    "type_id": type_id,
                    "type_name": type_name,
                    "region_id": region_id,
                    "region_name": region_name,
                    "current_price": cu["price"],
                    "baseline_price": bl["avg_price"],
                    "price_change_percent": round(price_chg, 2),
                    "current_volume": cu["volume"],
                    "baseline_volume": bl["avg_volume"],
                    "volume_change_percent": round(vol_chg, 2),
                    "z_score": round(combined_z, 2),
                    "severity": classify_severity(combined_z),
                    "manipulation_type": determine_manipulation_type(price_chg, vol_chg),
                })

    # Persist
    store_alerts(db, all_alerts)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    confirmed = sum(1 for a in all_alerts if a["severity"] == "confirmed")
    probable = sum(1 for a in all_alerts if a["severity"] == "probable")
    suspicious = sum(1 for a in all_alerts if a["severity"] == "suspicious")

    logger.info(
        f"Manipulation scan: {len(all_alerts)} alerts "
        f"(confirmed={confirmed}, probable={probable}, suspicious={suspicious}) "
        f"in {elapsed:.1f}s"
    )

    return {
        "status": "completed",
        "job": "scan-manipulation",
        "details": {
            "regions_scanned": len(MONITORED_REGIONS),
            "total_alerts": len(all_alerts),
            "confirmed": confirmed,
            "probable": probable,
            "suspicious": suspicious,
            "elapsed_seconds": round(elapsed, 2),
        },
    }
