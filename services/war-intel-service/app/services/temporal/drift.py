"""Drift detection — compare doctrine clusters across time windows."""

from dataclasses import dataclass
from typing import List, Dict, Any

DRIFT_NEW = "NEW"
DRIFT_DECLINING = "DECLINING"
DRIFT_RECYCLED = "RECYCLED"
DRIFT_ADAPTING = "ADAPTING"
DRIFT_STABLE = "STABLE"


@dataclass
class DriftSignal:
    drift_type: str
    ship_type_id: int
    cluster_id: int
    observation_count: int
    detail: str = ""


def _index_by_ship(clusters: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Index cluster list by ship_type_id for fast lookup."""
    return {c["ship_type_id"]: c for c in clusters}


def detect_drift(
    active: List[Dict[str, Any]],
    baseline: List[Dict[str, Any]],
    historical: List[Dict[str, Any]],
) -> List[DriftSignal]:
    """Compare clusters across 3 time windows and return drift signals."""
    signals: List[DriftSignal] = []

    active_idx = _index_by_ship(active)
    baseline_idx = _index_by_ship(baseline)
    historical_idx = _index_by_ship(historical)

    all_ships = set(active_idx) | set(baseline_idx) | set(historical_idx)

    for ship_id in all_ships:
        in_active = ship_id in active_idx
        in_baseline = ship_id in baseline_idx
        in_historical = ship_id in historical_idx

        cluster = active_idx.get(ship_id) or baseline_idx.get(ship_id) or historical_idx.get(ship_id)
        cluster_id = cluster["cluster_id"]
        obs = cluster["observation_count"]

        if in_active and not in_baseline and not in_historical:
            signals.append(DriftSignal(DRIFT_NEW, ship_id, cluster_id, obs, "New in active window"))
        elif in_active and not in_baseline and in_historical:
            signals.append(DriftSignal(DRIFT_RECYCLED, ship_id, cluster_id, obs, "Reappeared from historical"))
        elif not in_active and in_baseline:
            signals.append(DriftSignal(DRIFT_DECLINING, ship_id, cluster_id, obs, "Gone from active window"))
        elif not in_active and not in_baseline and in_historical:
            signals.append(DriftSignal(DRIFT_DECLINING, ship_id, cluster_id, obs, "Only in historical"))
        elif in_active and in_baseline:
            signals.append(DriftSignal(DRIFT_STABLE, ship_id, cluster_id, obs, "Present in both windows"))

    return signals
