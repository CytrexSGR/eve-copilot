"""
War Economy Data Models
Dataclasses for fuel snapshots, supercap timers, and manipulation alerts.
"""

from datetime import datetime, date
from typing import Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class FuelSnapshot:
    """Fuel market snapshot with anomaly detection"""
    isotope_type: str
    isotope_id: int
    region_id: int
    region_name: str
    current_volume: int
    baseline_volume: int
    volume_delta_percent: float
    average_price: float
    anomaly_detected: bool
    severity: str  # 'normal', 'low', 'medium', 'high', 'critical'
    timestamp: datetime

    def to_dict(self) -> Dict:
        """Convert to API response format"""
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
            'alert_message': self._get_alert_message() if self.anomaly_detected else None
        }

    def _get_alert_message(self) -> str:
        """Generate human-readable alert message"""
        direction = "spike" if self.volume_delta_percent > 0 else "drop"
        return (
            f"{self.severity.upper()}: {abs(self.volume_delta_percent):.1f}% "
            f"{self.isotope_type} {direction} in {self.region_name} - "
            f"Possible capital movement"
        )


@dataclass
class SupercapTimer:
    """Supercapital construction countdown"""
    id: int
    ship_type_id: int
    ship_name: str
    solar_system_id: int
    system_name: str
    region_name: str
    alliance_name: Optional[str]
    build_start_date: date
    estimated_completion: date
    days_remaining: int
    hours_remaining: int
    status: str
    confidence_level: str
    notes: Optional[str]

    def to_dict(self) -> Dict:
        """Convert to API response format"""
        return {
            **asdict(self),
            'build_start_date': self.build_start_date.isoformat(),
            'estimated_completion': self.estimated_completion.isoformat(),
            'strike_window': self._get_strike_window(),
            'alert_level': self._get_alert_level()
        }

    def _get_strike_window(self) -> str:
        """Calculate optimal strike timing"""
        if self.days_remaining <= 3:
            return "URGENT: Strike within 72h to prevent completion"
        elif self.days_remaining <= 7:
            return "HIGH: Strike within 1 week recommended"
        elif self.days_remaining <= 14:
            return "MEDIUM: 2 week strike window"
        else:
            return "LOW: Monitor for now"

    def _get_alert_level(self) -> str:
        """Alert level based on time remaining"""
        if self.days_remaining <= 3:
            return "critical"
        elif self.days_remaining <= 7:
            return "high"
        elif self.days_remaining <= 14:
            return "medium"
        else:
            return "low"


@dataclass
class ManipulationAlert:
    """Market manipulation detection result"""
    type_id: int
    type_name: str
    region_id: int
    region_name: str
    current_price: float
    baseline_price: float
    price_change_percent: float
    current_volume: int
    baseline_volume: int
    volume_change_percent: float
    z_score: float
    severity: str
    manipulation_type: str
    detected_at: datetime

    def to_dict(self) -> Dict:
        """Convert to API response format"""
        return {
            **asdict(self),
            'detected_at': self.detected_at.isoformat(),
            'context': self._get_context()
        }

    def _get_context(self) -> str:
        """Strategic context for manipulation"""
        if self.manipulation_type == 'combined':
            return f"Price and volume manipulation detected - likely pre-blockade preparation"
        elif self.manipulation_type == 'price_spike':
            return f"Artificial price inflation - market cornering attempt"
        else:
            return f"Volume anomaly - stockpiling or dumping in progress"
