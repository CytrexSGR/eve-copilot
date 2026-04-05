"""Fuel market scanner for capital movement prediction.

Tracks isotope market anomalies across trade hub regions
by comparing current prices/volumes against 7-day baselines.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from eve_shared.constants import REGION_NAMES, TRADE_HUB_REGIONS

logger = logging.getLogger(__name__)

# Isotope type IDs (capital ship fuel)
ISOTOPES = {
    "Hydrogen": 17889,   # Minmatar
    "Helium": 16274,     # Amarr
    "Nitrogen": 17888,   # Caldari
    "Oxygen": 17887,     # Gallente
}

MONITORED_REGIONS = list(TRADE_HUB_REGIONS.values())

FUEL_ANOMALY_THRESHOLD = 30.0  # % volume change for anomaly


def classify_anomaly(delta_pct: float) -> Tuple[bool, str]:
    """Classify volume anomaly by severity."""
    ad = abs(delta_pct)
    if ad >= 100:
        return True, "critical"
    elif ad >= 60:
        return True, "high"
    elif ad >= FUEL_ANOMALY_THRESHOLD:
        return True, "medium"
    elif ad >= 15:
        return True, "low"
    return False, "normal"


def bulk_fetch_current(db, region_ids: List[int], type_ids: List[int]) -> Dict[Tuple[int, int], Dict]:
    """Fetch current market data for isotopes."""
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT region_id, type_id,
                       COALESCE(sell_volume, 0) + COALESCE(buy_volume, 0) as total_volume,
                       COALESCE(lowest_sell, 0) as avg_price
                FROM market_prices
                WHERE region_id = ANY(%s) AND type_id = ANY(%s)
            """, (region_ids, type_ids))
            return {
                (row[0], row[1]): {"volume": row[2], "price": float(row[3]) if row[3] else 0.0}
                for row in cur.fetchall()
            }


def bulk_fetch_baselines(db, region_ids: List[int], type_ids: List[int], days: int = 7) -> Dict[Tuple[int, int], Dict]:
    """Fetch 7-day baseline stats from fuel snapshot history."""
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT region_id, isotope_type_id,
                       AVG(total_volume)::BIGINT as avg_volume,
                       AVG(average_price)::NUMERIC as avg_price,
                       STDDEV(total_volume)::NUMERIC as volume_stddev
                FROM war_economy_fuel_snapshots
                WHERE region_id = ANY(%s)
                  AND isotope_type_id = ANY(%s)
                  AND snapshot_time >= NOW() - INTERVAL '%s days'
                GROUP BY region_id, isotope_type_id
            """, (region_ids, type_ids, days))
            return {
                (row[0], row[1]): {
                    "volume": row[2] if row[2] else 0,
                    "price": float(row[3]) if row[3] else 0.0,
                    "stddev": float(row[4]) if row[4] else 0.0,
                }
                for row in cur.fetchall()
            }


def calculate_snapshots(current_data, baselines, region_ids) -> list:
    """Build snapshot dicts with anomaly classification."""
    snapshots = []
    timestamp = datetime.now(timezone.utc)
    isotope_names = {v: k for k, v in ISOTOPES.items()}

    for region_id in region_ids:
        for isotope_id in ISOTOPES.values():
            key = (region_id, isotope_id)
            cur = current_data.get(key, {"volume": 0, "price": 0.0})
            bl = baselines.get(key, {"volume": 0, "price": 0.0, "stddev": 0.0})
            delta = ((cur["volume"] - bl["volume"]) / bl["volume"] * 100) if bl["volume"] > 0 else 0.0
            anomaly, severity = classify_anomaly(delta)
            snapshots.append({
                "timestamp": timestamp,
                "region_id": region_id,
                "isotope_id": isotope_id,
                "isotope_name": isotope_names.get(isotope_id, f"Isotope {isotope_id}"),
                "current_volume": cur["volume"],
                "average_price": cur["price"],
                "baseline_volume": bl["volume"],
                "volume_delta_percent": round(delta, 2),
                "anomaly_detected": anomaly,
                "severity": severity,
            })
    return snapshots


def bulk_insert_snapshots(db, snapshots: list):
    """Bulk insert fuel snapshots with upsert."""
    if not snapshots:
        return
    with db.connection() as conn:
        with conn.cursor() as cur:
            for s in snapshots:
                cur.execute(
                    """
                    INSERT INTO war_economy_fuel_snapshots (
                        snapshot_time, region_id, isotope_type_id,
                        total_volume, average_price, baseline_7d_volume,
                        volume_delta_percent, anomaly_detected, anomaly_severity
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_time, region_id, isotope_type_id) DO UPDATE SET
                        total_volume = EXCLUDED.total_volume,
                        average_price = EXCLUDED.average_price,
                        baseline_7d_volume = EXCLUDED.baseline_7d_volume,
                        volume_delta_percent = EXCLUDED.volume_delta_percent,
                        anomaly_detected = EXCLUDED.anomaly_detected,
                        anomaly_severity = EXCLUDED.anomaly_severity
                    """,
                    (s["timestamp"], s["region_id"], s["isotope_id"],
                     s["current_volume"], s["average_price"], s["baseline_volume"],
                     s["volume_delta_percent"], s["anomaly_detected"], s["severity"]),
                )
            conn.commit()


def scan_fuel_markets(db) -> dict:
    """Scan fuel markets for anomalies across all trade hubs.

    Args:
        db: eve_shared DatabasePool instance.

    Returns:
        Job result dict.
    """
    start = datetime.now(timezone.utc)
    type_ids = list(ISOTOPES.values())

    current_data = bulk_fetch_current(db, MONITORED_REGIONS, type_ids)
    baselines = bulk_fetch_baselines(db, MONITORED_REGIONS, type_ids)
    snapshots = calculate_snapshots(current_data, baselines, MONITORED_REGIONS)
    bulk_insert_snapshots(db, snapshots)

    anomalies = [s for s in snapshots if s["anomaly_detected"]]
    critical = sum(1 for a in anomalies if a["severity"] in ("critical", "high"))

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(
        f"Fuel scan: {len(anomalies)} anomalies ({critical} critical/high) "
        f"from {len(snapshots)} snapshots in {elapsed:.1f}s"
    )

    return {
        "status": "completed",
        "job": "scan-fuel-markets",
        "details": {
            "regions_scanned": len(MONITORED_REGIONS),
            "snapshots_taken": len(snapshots),
            "anomalies_detected": len(anomalies),
            "critical_high": critical,
            "elapsed_seconds": round(elapsed, 2),
        },
    }
