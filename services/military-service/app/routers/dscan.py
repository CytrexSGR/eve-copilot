"""D-Scan Parser — Parse and analyze EVE Directional Scanner output.

Accepts raw D-Scan text (tab-separated: ID, Name, Type, Distance) from EVE
client copy-paste. Groups results by ship class, detects structures,
parses distance formats, and provides threat assessment.
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Body
from pydantic import Field

from app.models.base import CamelModel
from app.database import sde_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Ship Classification (mirrors corp_sql_helpers.py — kept inline for speed)
# =============================================================================

_SHIP_CLASSES = {
    'Frigate': {
        'Frigate', 'Assault Frigate', 'Interceptor', 'Covert Ops',
        'Electronic Attack Ship', 'Stealth Bomber', 'Expedition Frigate',
        'Logistics Frigate', 'Prototype Exploration Ship',
    },
    'Destroyer': {
        'Destroyer', 'Interdictor', 'Tactical Destroyer', 'Command Destroyer',
    },
    'Cruiser': {
        'Cruiser', 'Heavy Assault Cruiser', 'Strategic Cruiser', 'Recon Ship',
        'Heavy Interdiction Cruiser', 'Logistics Cruiser', 'Logistics',
        'Combat Recon Ship', 'Force Recon Ship', 'Flag Cruiser',
        'Expedition Command Ship',
    },
    'Battlecruiser': {
        'Battlecruiser', 'Command Ship', 'Attack Battlecruiser',
        'Combat Battlecruiser',
    },
    'Battleship': {
        'Battleship', 'Black Ops', 'Marauder', 'Elite Battleship',
    },
    'Capital': {
        'Carrier', 'Dreadnought', '\u2666 Dreadnought', 'Lancer Dreadnought',
        'Force Auxiliary', 'Supercarrier', 'Titan',
        'Capital Industrial Ship', 'Jump Freighter',
    },
    'Industrial': {
        'Mining Barge', 'Exhumer', 'Industrial', 'Transport Ship',
        'Deep Space Transport', 'Blockade Runner', 'Freighter',
        'Industrial Command Ship',
    },
}

_STRUCTURE_GROUPS = {
    'Citadel', 'Engineering Complex', '\u2666 Engineering Complex', 'Refinery',
    'Administration Hub', 'Observatory', 'Stargate', 'Upwell Jump Gate',
    'Control Tower', 'Infrastructure Upgrades',
}

_DEPLOYABLE_GROUPS = {
    'Mobile Warp Disruptor', 'Mobile Cyno Inhibitor', 'Mobile Depot',
    'Mobile Siphon Unit', 'Mobile Scan Inhibitor', 'Mobile Micro Jump Unit',
    'Mercenary Den', 'Upwell Moon Drill', 'Upwell Cyno Jammer',
    'Upwell Cyno Beacon', 'Deployable', 'Mobile Tractor Unit', 'Skyhook',
    'Mobile Phase Anchor',
}

_CAPSULE_GROUPS = {'Capsule', 'Rookie ship', 'Shuttle', 'Corvette'}

# Build reverse lookup: group_name → class
_GROUP_TO_CLASS: dict[str, str] = {}
for _cls, _groups in _SHIP_CLASSES.items():
    for _g in _groups:
        _GROUP_TO_CLASS[_g] = _cls
for _g in _STRUCTURE_GROUPS:
    _GROUP_TO_CLASS[_g] = 'Structure'
for _g in _DEPLOYABLE_GROUPS:
    _GROUP_TO_CLASS[_g] = 'Deployable'
for _g in _CAPSULE_GROUPS:
    _GROUP_TO_CLASS[_g] = 'Capsule'


def _classify(group_name: str) -> str:
    return _GROUP_TO_CLASS.get(group_name, 'Other')


# =============================================================================
# Distance parsing
# =============================================================================

_AU_KM = 149_597_870.7  # 1 AU in km

_DIST_RE = re.compile(
    r'([\d,\.]+)\s*(km|m|AU)',
    re.IGNORECASE,
)


def _parse_distance(raw: str) -> Optional[float]:
    """Parse EVE distance string to km. Returns None if unparseable."""
    raw = raw.strip().replace('\xa0', ' ')
    if raw == '-' or not raw:
        return None
    m = _DIST_RE.search(raw)
    if not m:
        return None
    num = float(m.group(1).replace(',', '').replace(' ', ''))
    unit = m.group(2).upper()
    if unit == 'AU':
        return num * _AU_KM
    if unit == 'M':
        return num / 1000.0
    return num  # km


# =============================================================================
# Models
# =============================================================================

class DscanParseRequest(CamelModel):
    raw_text: str = Field(..., description="Raw D-Scan paste from EVE client")


class DscanCompareRequest(CamelModel):
    scan_a: str = Field(..., description="First D-Scan paste")
    scan_b: str = Field(..., description="Second D-Scan paste (newer)")


class DscanShip(CamelModel):
    type_id: int
    type_name: str
    group_name: str
    ship_class: str
    distance_km: Optional[float] = None
    count: int = 1


class DscanClassBreakdown(CamelModel):
    ship_class: str
    count: int
    types: list[dict]


class DscanResult(CamelModel):
    total_items: int
    total_ships: int
    ship_classes: list[DscanClassBreakdown]
    structures: list[dict]
    deployables: list[dict]
    capsules: int = 0
    threat_level: str = Field(
        ..., description="none / low / medium / high / critical"
    )
    threat_summary: str = ""
    unknown_lines: int = 0


class DscanCompareResult(CamelModel):
    new_ships: list[dict]
    gone_ships: list[dict]
    new_count: int
    gone_count: int
    delta_by_class: dict


# =============================================================================
# Helpers
# =============================================================================

def _parse_dscan_lines(raw_text: str) -> list[dict]:
    """Parse raw D-Scan text into list of item dicts.

    EVE D-Scan format (tab-separated):
        <type_id>\t<name>\t<type_name>\t<distance>
    """
    items = []
    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) < 3:
            continue
        try:
            type_id = int(parts[0])
        except (ValueError, IndexError):
            continue
        name = parts[1].strip()
        type_name = parts[2].strip()
        distance_raw = parts[3].strip() if len(parts) > 3 else ''
        items.append({
            'type_id': type_id,
            'type_name': type_name,
            'name': name,
            'distance_km': _parse_distance(distance_raw),
        })
    return items


def _resolve_groups(items: list[dict]) -> list[dict]:
    """Resolve type_id → groupName from SDE invTypes + invGroups."""
    if not items:
        return items
    type_ids = list({i['type_id'] for i in items})
    group_map: dict[int, str] = {}
    with sde_cursor() as cur:
        # Batch resolve in chunks of 500
        for i in range(0, len(type_ids), 500):
            chunk = type_ids[i:i + 500]
            placeholders = ','.join(['%s'] * len(chunk))
            cur.execute(f"""
                SELECT t."typeID", g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE t."typeID" IN ({placeholders})
            """, chunk)
            for row in cur.fetchall():
                group_map[row['typeID']] = row['groupName']

    for item in items:
        gn = group_map.get(item['type_id'], '')
        item['group_name'] = gn
        item['ship_class'] = _classify(gn)
    return items


def _assess_threat(class_counts: dict[str, int]) -> tuple[str, str]:
    """Determine threat level from ship class counts."""
    caps = class_counts.get('Capital', 0)
    bs = class_counts.get('Battleship', 0)
    bc = class_counts.get('Battlecruiser', 0)
    cruisers = class_counts.get('Cruiser', 0)
    destroyers = class_counts.get('Destroyer', 0)
    frigates = class_counts.get('Frigate', 0)
    total_combat = caps + bs + bc + cruisers + destroyers + frigates

    if total_combat == 0:
        return 'none', 'No combat ships detected'
    if caps >= 5 or total_combat >= 100:
        return 'critical', f'{total_combat} combat ships ({caps} capitals)'
    if caps >= 1 or total_combat >= 30:
        return 'high', f'{total_combat} combat ships ({caps} capitals)'
    if bs >= 3 or total_combat >= 10:
        return 'medium', f'{total_combat} combat ships'
    if total_combat >= 3:
        return 'low', f'{total_combat} combat ships'
    return 'low', f'{total_combat} combat ship(s)'


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/dscan/parse", response_model=DscanResult)
@handle_endpoint_errors()
def parse_dscan(req: DscanParseRequest = Body(...)):
    """Parse raw D-Scan text and return grouped analysis."""
    raw_items = _parse_dscan_lines(req.raw_text)
    unknown_lines = req.raw_text.strip().count('\n') + 1 - len(raw_items) if raw_items else 0
    if unknown_lines < 0:
        unknown_lines = 0

    items = _resolve_groups(raw_items)

    # Group by ship class
    class_types: dict[str, dict[int, dict]] = {}
    structures = []
    deployables = []
    capsules = 0
    ship_count = 0

    for item in items:
        sc = item['ship_class']
        if sc == 'Structure':
            structures.append({
                'type_name': item['type_name'],
                'name': item['name'],
                'distance_km': item['distance_km'],
            })
            continue
        if sc == 'Deployable':
            deployables.append({
                'type_name': item['type_name'],
                'name': item['name'],
                'distance_km': item['distance_km'],
            })
            continue
        if sc == 'Capsule':
            capsules += 1
            continue

        ship_count += 1
        if sc not in class_types:
            class_types[sc] = {}
        tid = item['type_id']
        if tid not in class_types[sc]:
            class_types[sc][tid] = {
                'type_id': tid,
                'type_name': item['type_name'],
                'count': 0,
            }
        class_types[sc][tid]['count'] += 1

    # Build class breakdown sorted by combat priority
    priority = ['Capital', 'Battleship', 'Battlecruiser', 'Cruiser',
                'Destroyer', 'Frigate', 'Industrial', 'Other']
    class_counts = {}
    ship_classes = []
    for cls in priority:
        if cls not in class_types:
            continue
        types_list = sorted(
            class_types[cls].values(),
            key=lambda t: -t['count'],
        )
        total = sum(t['count'] for t in types_list)
        class_counts[cls] = total
        ship_classes.append(DscanClassBreakdown(
            ship_class=cls,
            count=total,
            types=types_list,
        ))

    # Also add any classes not in priority
    for cls in sorted(class_types.keys()):
        if cls in priority:
            continue
        types_list = sorted(class_types[cls].values(), key=lambda t: -t['count'])
        total = sum(t['count'] for t in types_list)
        class_counts[cls] = total
        ship_classes.append(DscanClassBreakdown(
            ship_class=cls, count=total, types=types_list,
        ))

    threat_level, threat_summary = _assess_threat(class_counts)

    return DscanResult(
        total_items=len(items),
        total_ships=ship_count,
        ship_classes=ship_classes,
        structures=structures,
        deployables=deployables,
        capsules=capsules,
        threat_level=threat_level,
        threat_summary=threat_summary,
        unknown_lines=unknown_lines,
    )


@router.post("/dscan/compare", response_model=DscanCompareResult)
@handle_endpoint_errors()
def compare_dscan(req: DscanCompareRequest = Body(...)):
    """Compare two D-Scan results to detect fleet changes."""
    items_a = _resolve_groups(_parse_dscan_lines(req.scan_a))
    items_b = _resolve_groups(_parse_dscan_lines(req.scan_b))

    # Build type_id → count maps
    def _type_counts(items):
        counts = {}
        for i in items:
            if i['ship_class'] in ('Structure', 'Deployable', 'Capsule'):
                continue
            tid = i['type_id']
            counts[tid] = counts.get(tid, 0) + 1
        return counts

    counts_a = _type_counts(items_a)
    counts_b = _type_counts(items_b)

    # Type name lookup
    name_map = {}
    class_map = {}
    for i in items_a + items_b:
        name_map[i['type_id']] = i['type_name']
        class_map[i['type_id']] = i['ship_class']

    new_ships = []
    gone_ships = []
    delta_by_class: dict[str, int] = {}

    all_types = set(counts_a.keys()) | set(counts_b.keys())
    for tid in all_types:
        ca = counts_a.get(tid, 0)
        cb = counts_b.get(tid, 0)
        diff = cb - ca
        if diff == 0:
            continue
        sc = class_map.get(tid, 'Other')
        delta_by_class[sc] = delta_by_class.get(sc, 0) + diff
        entry = {
            'type_id': tid,
            'type_name': name_map.get(tid, f'Unknown ({tid})'),
            'ship_class': sc,
            'delta': abs(diff),
        }
        if diff > 0:
            new_ships.append(entry)
        else:
            gone_ships.append(entry)

    return DscanCompareResult(
        new_ships=sorted(new_ships, key=lambda s: -s['delta']),
        gone_ships=sorted(gone_ships, key=lambda s: -s['delta']),
        new_count=sum(s['delta'] for s in new_ships),
        gone_count=sum(s['delta'] for s in gone_ships),
        delta_by_class=delta_by_class,
    )
