"""
Manipulation Detector
Detects market manipulation using Z-score analysis.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import statistics

from psycopg2.extras import RealDictCursor

from src.database import get_db_connection
from config import REGIONS
from services.war_economy.models import ManipulationAlert
from services.war_economy.config import CRITICAL_ITEMS, MANIPULATION_Z_SCORE_THRESHOLD


logger = logging.getLogger(__name__)


class ManipulationDetector:
    """Detects market manipulation using statistical analysis."""

    def __init__(self, db_pool):
        self.db_pool = db_pool

    def scan_region(self, region_id: int, days_lookback: int = 30) -> List[ManipulationAlert]:
        """Scan region for market manipulation."""
        logger.info(f"Scanning region {region_id} for manipulation")

        # 1. Get baseline statistics (30-day average)
        baselines = self._fetch_baselines(region_id, list(CRITICAL_ITEMS.values()), days_lookback)

        # 2. Get current prices
        current_prices = self._fetch_current_prices(region_id, list(CRITICAL_ITEMS.values()))

        # 3. Analyze for manipulation
        alerts = []
        region_name = REGIONS.get(region_id, f"Region {region_id}")

        for type_name, type_id in CRITICAL_ITEMS.items():
            if type_id not in baselines or type_id not in current_prices:
                continue

            baseline = baselines[type_id]
            current = current_prices[type_id]

            # Calculate Z-scores
            price_z = self._calculate_z_score(
                current['price'],
                baseline['avg_price'],
                baseline['price_stddev']
            )

            volume_z = self._calculate_z_score(
                current['volume'],
                baseline['avg_volume'],
                baseline['volume_stddev']
            )

            # Combined Z-score (RMS)
            combined_z = (price_z ** 2 + volume_z ** 2) ** 0.5

            if combined_z >= MANIPULATION_Z_SCORE_THRESHOLD:
                price_change = ((current['price'] - baseline['avg_price']) / baseline['avg_price']) * 100
                volume_change = ((current['volume'] - baseline['avg_volume']) / baseline['avg_volume']) * 100

                severity = self._classify_severity(combined_z)
                manipulation_type = self._determine_manipulation_type(price_change, volume_change)

                alert = ManipulationAlert(
                    type_id=type_id,
                    type_name=type_name,
                    region_id=region_id,
                    region_name=region_name,
                    current_price=current['price'],
                    baseline_price=baseline['avg_price'],
                    price_change_percent=price_change,
                    current_volume=current['volume'],
                    baseline_volume=baseline['avg_volume'],
                    volume_change_percent=volume_change,
                    z_score=combined_z,
                    severity=severity,
                    manipulation_type=manipulation_type,
                    detected_at=datetime.utcnow()
                )
                alerts.append(alert)

        logger.info(f"Detected {len(alerts)} manipulation alerts in region {region_id}")
        return alerts

    def store_alerts(self, alerts: List[ManipulationAlert]):
        """Store alerts in database."""
        if not alerts:
            return

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for alert in alerts:
                    cur.execute('''
                        INSERT INTO war_economy_manipulation_alerts (
                            type_id, type_name, region_id, region_name,
                            current_price, baseline_price, price_change_percent,
                            current_volume, baseline_volume, volume_change_percent,
                            z_score, severity, manipulation_type
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        alert.type_id, alert.type_name, alert.region_id, alert.region_name,
                        alert.current_price, alert.baseline_price, alert.price_change_percent,
                        alert.current_volume, alert.baseline_volume, alert.volume_change_percent,
                        alert.z_score, alert.severity, alert.manipulation_type
                    ))
                conn.commit()
                logger.info(f"Stored {len(alerts)} manipulation alerts")

    def _fetch_baselines(self, region_id: int, type_ids: List[int], days: int) -> Dict[int, Dict]:
        """
        Fetch baseline statistics from price history table.
        Uses actual historical data for proper Z-score calculation.
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Calculate mean and stddev from price history
                cur.execute('''
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
                ''', (region_id, type_ids, days))

                results = {}
                for row in cur.fetchall():
                    # Ensure stddev is at least 1% of mean to avoid division issues
                    avg_price = float(row['avg_price']) if row['avg_price'] else 0
                    price_stddev = float(row['price_stddev']) if row['price_stddev'] else 0
                    avg_volume = float(row['avg_volume']) if row['avg_volume'] else 0
                    volume_stddev = float(row['volume_stddev']) if row['volume_stddev'] else 0

                    # Minimum stddev is 1% of mean (prevents zero division)
                    if price_stddev < avg_price * 0.01:
                        price_stddev = max(avg_price * 0.01, 1.0)
                    if volume_stddev < avg_volume * 0.01:
                        volume_stddev = max(avg_volume * 0.01, 1.0)

                    results[row['type_id']] = {
                        'avg_price': avg_price,
                        'price_stddev': price_stddev,
                        'avg_volume': avg_volume,
                        'volume_stddev': volume_stddev,
                        'sample_count': row['sample_count']
                    }

                return results

    def _fetch_current_prices(self, region_id: int, type_ids: List[int]) -> Dict[int, Dict]:
        """Fetch current market prices."""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT
                        type_id,
                        COALESCE(lowest_sell, 0) as price,
                        COALESCE(sell_volume, 0) + COALESCE(buy_volume, 0) as volume
                    FROM market_prices
                    WHERE region_id = %s
                    AND type_id = ANY(%s)
                ''', (region_id, type_ids))

                return {
                    row['type_id']: {
                        'price': float(row['price']),
                        'volume': row['volume']
                    }
                    for row in cur.fetchall()
                }

    def _calculate_z_score(self, value: float, mean: float, stddev: float) -> float:
        """Calculate Z-score."""
        if stddev == 0:
            return 0.0
        return abs((value - mean) / stddev)

    def _classify_severity(self, z_score: float) -> str:
        """Classify manipulation severity based on Z-score."""
        if z_score >= 4.0:
            return 'confirmed'  # 99.99% confidence
        elif z_score >= 3.0:
            return 'probable'   # 99.7% confidence
        elif z_score >= MANIPULATION_Z_SCORE_THRESHOLD:
            return 'suspicious' # 98.7% confidence
        else:
            return 'normal'

    def _determine_manipulation_type(self, price_change: float, volume_change: float) -> str:
        """Determine type of manipulation."""
        price_significant = abs(price_change) > 50
        volume_significant = abs(volume_change) > 50

        if price_significant and volume_significant:
            return 'combined'
        elif price_significant:
            return 'price_spike'
        else:
            return 'volume_anomaly'
