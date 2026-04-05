"""
War Economy Service
Main coordinator for economic warfare intelligence.
"""

from typing import List, Optional
import logging

from services.war_economy.fuel_tracker import FuelTracker
from services.war_economy.supercap_manager import SupercapTimerManager
from services.war_economy.manipulation_detector import ManipulationDetector
from services.war_economy.models import FuelSnapshot, SupercapTimer, ManipulationAlert


logger = logging.getLogger(__name__)


class WarEconomyService:
    """
    Main coordinator for War Economy features.

    Integrates:
    - FuelTracker: Isotope market anomaly detection
    - SupercapTimerManager: Construction timer tracking
    - ManipulationDetector: Market manipulation detection
    """

    def __init__(self, db_pool, market_service):
        """Initialize with database pool and market service."""
        self.db_pool = db_pool
        self.market_service = market_service

        # Initialize subsystems
        self.fuel_tracker = FuelTracker(db_pool, market_service)
        self.supercap_manager = SupercapTimerManager(db_pool)
        self.manipulation_detector = ManipulationDetector(db_pool)

        logger.info("WarEconomyService initialized")

    # ============================================================
    # FUEL TRACKING
    # ============================================================

    def scan_fuel_markets(self, region_ids: List[int]) -> List[FuelSnapshot]:
        """
        Scan fuel markets for anomalies.

        Returns: List of detected anomalies
        """
        logger.info(f"Scanning fuel markets for {len(region_ids)} regions")
        return self.fuel_tracker.snapshot_all(region_ids)

    def get_fuel_trends(self, region_id: int, hours: int = 24) -> List[dict]:
        """Get fuel market trends for API endpoint."""
        return self.fuel_tracker.get_trends(region_id, hours)

    # ============================================================
    # SUPERCAP TIMERS
    # ============================================================

    def get_active_supercap_timers(self, region_id: Optional[int] = None) -> List[SupercapTimer]:
        """Get all active supercap construction timers."""
        return self.supercap_manager.get_active_timers(region_id)

    def add_supercap_timer(
        self,
        solar_system_id: int,
        ship_type_id: int,
        build_start_date,
        estimated_completion_date,
        **kwargs
    ) -> int:
        """Add new supercap timer."""
        return self.supercap_manager.add_timer(
            solar_system_id,
            ship_type_id,
            build_start_date,
            estimated_completion_date,
            **kwargs
        )

    def update_supercap_timer_status(self, timer_id: int, status: str):
        """Update timer status."""
        self.supercap_manager.update_status(timer_id, status)

    def update_supercap_timer(self, timer_id: int, **kwargs):
        """Update timer details."""
        self.supercap_manager.update_timer(timer_id, **kwargs)

    # ============================================================
    # MARKET MANIPULATION
    # ============================================================

    def scan_manipulation(self, region_id: int, days_lookback: int = 30) -> List[ManipulationAlert]:
        """
        Scan region for market manipulation.

        Returns: List of detected manipulation alerts
        """
        logger.info(f"Scanning region {region_id} for manipulation")
        alerts = self.manipulation_detector.scan_region(region_id, days_lookback)

        # Store alerts in database
        if alerts:
            self.manipulation_detector.store_alerts(alerts)

        return alerts

    def get_manipulation_alerts(self, region_id: Optional[int] = None, hours: int = 24) -> List[dict]:
        """Get recent manipulation alerts from database."""
        from psycopg2.extras import RealDictCursor
        from src.database import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = '''
                    SELECT
                        id, type_id, type_name, region_id, region_name,
                        current_price, baseline_price, price_change_percent,
                        current_volume, baseline_volume, volume_change_percent,
                        z_score, severity, manipulation_type, detected_at
                    FROM war_economy_manipulation_alerts
                    WHERE detected_at >= NOW() - INTERVAL '%s hours'
                '''
                params = [hours]

                if region_id:
                    query += ' AND region_id = %s'
                    params.append(region_id)

                query += ' ORDER BY z_score DESC, detected_at DESC'

                cur.execute(query, params)
                rows = cur.fetchall()

                return [
                    {
                        'id': row['id'],
                        'type_id': row['type_id'],
                        'type_name': row['type_name'],
                        'region_id': row['region_id'],
                        'region_name': row['region_name'],
                        'current_price': float(row['current_price']),
                        'baseline_price': float(row['baseline_price']),
                        'price_change_percent': float(row['price_change_percent']),
                        'current_volume': row['current_volume'],
                        'baseline_volume': row['baseline_volume'],
                        'volume_change_percent': float(row['volume_change_percent']),
                        'z_score': float(row['z_score']),
                        'severity': row['severity'],
                        'manipulation_type': row['manipulation_type'],
                        'detected_at': row['detected_at'].isoformat()
                    }
                    for row in rows
                ]

    # ============================================================
    # COMBINED ANALYSIS
    # ============================================================

    def get_regional_overview(self, region_id: int) -> dict:
        """
        Get comprehensive regional economic intelligence.

        Returns: Dict with fuel trends, manipulation alerts, and supercap timers
        """
        logger.info(f"Generating regional overview for region {region_id}")

        return {
            'region_id': region_id,
            'fuel_trends': self.get_fuel_trends(region_id, hours=24),
            'manipulation_alerts': self.get_manipulation_alerts(region_id),
            'supercap_timers': [
                t.to_dict() for t in self.get_active_supercap_timers(region_id)
            ]
        }
