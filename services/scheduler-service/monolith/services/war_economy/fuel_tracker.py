"""
Fuel Tracker Subsystem
Isotope purchase tracking for capital movement prediction.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict
import logging

from psycopg2.extras import execute_values, RealDictCursor

from src.database import get_db_connection
from config import REGIONS
from services.war_economy.models import FuelSnapshot
from services.war_economy.config import ISOTOPES, FUEL_ANOMALY_THRESHOLD


logger = logging.getLogger(__name__)


class FuelTracker:
    """
    Isotope purchase tracking for capital movement prediction.

    Uses bulk operations for performance:
    - Single query for all current market data
    - Single query for all baselines
    - Bulk insert for snapshots
    """

    def __init__(self, db_pool, market_service):
        self.db_pool = db_pool
        self.market = market_service

    def snapshot_all(self, region_ids: List[int]) -> List[FuelSnapshot]:
        """
        Take snapshots of all isotope markets.

        Returns: List of anomalies detected (only snapshots with anomaly_detected=True)
        """
        logger.info(f"Starting fuel snapshot for {len(region_ids)} regions")

        # 1. Bulk fetch current market data
        current_data = self._bulk_fetch_current(region_ids, list(ISOTOPES.values()))

        # 2. Bulk fetch baselines
        baselines = self._bulk_fetch_baselines(region_ids, list(ISOTOPES.values()))

        # 3. Calculate snapshots
        snapshots = self._calculate_snapshots(current_data, baselines, region_ids)

        # 4. Bulk insert (idempotent)
        self._bulk_insert(snapshots)

        # 5. Return anomalies only
        anomalies = [s for s in snapshots if s.anomaly_detected]
        logger.info(f"Detected {len(anomalies)} fuel anomalies")

        return anomalies

    def _bulk_fetch_current(self, region_ids: List[int], type_ids: List[int]) -> Dict[Tuple[int, int], Dict]:
        """Fetch current market data for all region/isotope combinations."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        region_id,
                        type_id,
                        COALESCE(sell_volume, 0) + COALESCE(buy_volume, 0) as total_volume,
                        COALESCE(lowest_sell, 0) as avg_price
                    FROM market_prices
                    WHERE region_id = ANY(%s)
                    AND type_id = ANY(%s)
                ''', (region_ids, type_ids))

                return {
                    (row[0], row[1]): {
                        'volume': row[2],
                        'price': float(row[3]) if row[3] else 0.0
                    }
                    for row in cur.fetchall()
                }

    def _bulk_fetch_baselines(self, region_ids: List[int], type_ids: List[int], days: int = 7) -> Dict[Tuple[int, int], Dict]:
        """Fetch 7-day baselines for all region/isotope combinations."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT
                        region_id,
                        isotope_type_id,
                        AVG(total_volume)::BIGINT as avg_volume,
                        AVG(average_price)::NUMERIC as avg_price,
                        STDDEV(total_volume)::NUMERIC as volume_stddev
                    FROM war_economy_fuel_snapshots
                    WHERE region_id = ANY(%s)
                    AND isotope_type_id = ANY(%s)
                    AND snapshot_time >= NOW() - INTERVAL '%s days'
                    GROUP BY region_id, isotope_type_id
                ''', (region_ids, type_ids, days))

                return {
                    (row[0], row[1]): {
                        'volume': row[2] if row[2] else 0,
                        'price': float(row[3]) if row[3] else 0.0,
                        'stddev': float(row[4]) if row[4] else 0.0
                    }
                    for row in cur.fetchall()
                }

    def _calculate_snapshots(self, current_data: Dict, baselines: Dict, region_ids: List[int]) -> List[FuelSnapshot]:
        """Calculate snapshots with anomaly detection."""
        snapshots = []
        timestamp = datetime.utcnow()
        isotope_names = {v: k for k, v in ISOTOPES.items()}

        for region_id in region_ids:
            region_name = REGIONS.get(region_id, f"Region {region_id}")

            for isotope_id in ISOTOPES.values():
                isotope_name = isotope_names.get(isotope_id, f"Isotope {isotope_id}")
                key = (region_id, isotope_id)

                current = current_data.get(key, {'volume': 0, 'price': 0.0})
                baseline = baselines.get(key, {'volume': 0, 'price': 0.0, 'stddev': 0.0})

                if baseline['volume'] > 0:
                    delta_percent = ((current['volume'] - baseline['volume']) / baseline['volume']) * 100
                else:
                    delta_percent = 0.0

                anomaly, severity = self._classify_anomaly(delta_percent)

                snapshot = FuelSnapshot(
                    isotope_type=isotope_name,
                    isotope_id=isotope_id,
                    region_id=region_id,
                    region_name=region_name,
                    current_volume=current['volume'],
                    baseline_volume=baseline['volume'],
                    volume_delta_percent=delta_percent,
                    average_price=current['price'],
                    anomaly_detected=anomaly,
                    severity=severity,
                    timestamp=timestamp
                )

                snapshots.append(snapshot)

        return snapshots

    def _classify_anomaly(self, delta_percent: float) -> Tuple[bool, str]:
        """Classify volume anomaly by severity."""
        abs_delta = abs(delta_percent)

        if abs_delta >= 100:
            return (True, 'critical')
        elif abs_delta >= 60:
            return (True, 'high')
        elif abs_delta >= FUEL_ANOMALY_THRESHOLD:
            return (True, 'medium')
        elif abs_delta >= 15:
            return (True, 'low')
        else:
            return (False, 'normal')

    def _bulk_insert(self, snapshots: List[FuelSnapshot]):
        """Bulk insert snapshots with idempotency."""
        if not snapshots:
            return

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                data = [
                    (s.timestamp, s.region_id, s.isotope_id, s.current_volume,
                     s.average_price, s.baseline_volume, s.volume_delta_percent,
                     s.anomaly_detected, s.severity)
                    for s in snapshots
                ]

                execute_values(
                    cur,
                    '''
                    INSERT INTO war_economy_fuel_snapshots (
                        snapshot_time, region_id, isotope_type_id,
                        total_volume, average_price, baseline_7d_volume,
                        volume_delta_percent, anomaly_detected, anomaly_severity
                    ) VALUES %s
                    ON CONFLICT (snapshot_time, region_id, isotope_type_id)
                    DO UPDATE SET
                        total_volume = EXCLUDED.total_volume,
                        average_price = EXCLUDED.average_price,
                        baseline_7d_volume = EXCLUDED.baseline_7d_volume,
                        volume_delta_percent = EXCLUDED.volume_delta_percent,
                        anomaly_detected = EXCLUDED.anomaly_detected,
                        anomaly_severity = EXCLUDED.anomaly_severity
                    ''',
                    data
                )
                conn.commit()

    def get_trends(self, region_id: int, hours: int = 24) -> List[Dict]:
        """Get fuel trends for API endpoint."""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT
                        snapshot_time,
                        isotope_type_id,
                        total_volume,
                        baseline_7d_volume,
                        volume_delta_percent,
                        average_price,
                        anomaly_detected,
                        anomaly_severity
                    FROM war_economy_fuel_snapshots
                    WHERE region_id = %s
                    AND snapshot_time >= NOW() - INTERVAL '%s hours'
                    ORDER BY snapshot_time DESC, isotope_type_id
                ''', (region_id, hours))

                rows = cur.fetchall()
                isotope_names = {v: k for k, v in ISOTOPES.items()}
                trends = defaultdict(lambda: {'snapshots': []})

                for row in rows:
                    isotope_id = row['isotope_type_id']
                    isotope_name = isotope_names.get(isotope_id, f"Isotope {isotope_id}")

                    if not trends[isotope_name].get('isotope_id'):
                        trends[isotope_name]['isotope_id'] = isotope_id
                        trends[isotope_name]['isotope_name'] = isotope_name

                    trends[isotope_name]['snapshots'].append({
                        'timestamp': row['snapshot_time'].isoformat(),
                        'volume': row['total_volume'],
                        'baseline': row['baseline_7d_volume'],
                        'delta_percent': float(row['volume_delta_percent']) if row['volume_delta_percent'] else 0,
                        'price': float(row['average_price']) if row['average_price'] else 0,
                        'anomaly': row['anomaly_detected'],
                        'severity': row['anomaly_severity']
                    })

                return list(trends.values())
