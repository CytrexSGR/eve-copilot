"""
Fleet Composition Optimizer Router - Counter-doctrine with LLM assistance.

Analyzes enemy doctrines and suggests optimal counter-fleets with
specific fits, numbers, and positioning advice.

Migrated to military-service with split-DB architecture:
- fleet_doctrines, intel_kills -> db_cursor() (military_db)
- invTypes -> sde_cursor() (SDE DB)
"""

import logging
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import httpx

from app.database import db_cursor, sde_cursor
from app.services.doctrine_stats_client import get_doctrine_stats, resolve_doctrine_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# Models
# ==============================================================================

class DoctrineInput(BaseModel):
    """Input doctrine to counter."""
    doctrine_name: str = Field(..., description="e.g., 'Ferox Fleet', 'Muninn Fleet'")
    ship_name: str
    estimated_count: int = 30
    tank_type: str = "shield"  # shield, armor
    engagement_range: str = "medium"  # short, medium, long
    avg_dps: float = 400
    weapon_type: Optional[str] = None


class CounterFleet(BaseModel):
    """Recommended counter fleet composition."""
    doctrine_name: str
    ships: List[Dict]
    total_dps: float
    engagement_advice: str
    positioning: str
    confidence: float
    notes: Optional[str] = None


# ==============================================================================
# Counter Doctrine Database
# ==============================================================================

# Known doctrines with detailed ship fits
KNOWN_DOCTRINES = {
    "Ferox Fleet": {
        "tank": "shield",
        "range": "medium",
        "avg_dps": 400,
        "weapon": "railgun",
        "counters": ["Muninn Fleet", "Nightmare Fleet"]
    },
    "Muninn Fleet": {
        "tank": "armor",
        "range": "long",
        "avg_dps": 520,
        "weapon": "artillery",
        "counters": ["Cerberus Fleet", "Eagle Fleet"]
    },
    "Cerberus Fleet": {
        "tank": "shield",
        "range": "long",
        "avg_dps": 480,
        "weapon": "missiles",
        "counters": ["Eagle Fleet", "Loki Fleet"]
    },
    "Eagle Fleet": {
        "tank": "shield",
        "range": "long",
        "avg_dps": 380,
        "weapon": "railgun",
        "counters": ["Sacrilege Fleet", "Muninn Fleet"]
    },
    "Hurricane Fleet": {
        "tank": "armor",
        "range": "medium",
        "avg_dps": 500,
        "weapon": "artillery",
        "counters": ["Ferox Fleet", "Cerberus Fleet"]
    },
    "Ishtar Fleet": {
        "tank": "armor",
        "range": "medium",
        "avg_dps": 450,
        "weapon": "drones",
        "counters": ["Cerberus Fleet", "Anti-Support"]
    },
    "Nightmare Fleet": {
        "tank": "armor",
        "range": "long",
        "avg_dps": 600,
        "weapon": "beam",
        "counters": ["Loki Fleet", "Machariel Fleet"]
    },
    "Sacrilege Fleet": {
        "tank": "armor",
        "range": "short",
        "avg_dps": 550,
        "weapon": "missiles",
        "counters": ["Kiting HACs", "Superior Numbers"]
    }
}

# Counter fleet compositions
COUNTER_COMPOSITIONS = {
    "Muninn Fleet": {
        "main": {"ship": "Muninn", "count_ratio": 1.0, "role": "DPS"},
        "logi": {"ship": "Scimitar", "count_ratio": 0.2, "role": "Logistics"},
        "tackle": {"ship": "Sabre", "count_ratio": 0.1, "role": "Tackle/Interdictor"},
        "links": {"ship": "Claymore", "count_ratio": 0.03, "role": "Command"},
        "base_dps": 520,
        "engagement": "Maintain 50-70km range, alpha through their logi",
        "positioning": "Aligned out, ready to kite. Keep transversal high."
    },
    "Cerberus Fleet": {
        "main": {"ship": "Cerberus", "count_ratio": 1.0, "role": "DPS"},
        "logi": {"ship": "Osprey", "count_ratio": 0.2, "role": "Logistics"},
        "tackle": {"ship": "Sabre", "count_ratio": 0.1, "role": "Tackle/Interdictor"},
        "links": {"ship": "Vulture", "count_ratio": 0.03, "role": "Command"},
        "base_dps": 480,
        "engagement": "Maintain 80-100km range, missiles ignore tracking",
        "positioning": "Aligned to celestial, keep at max range."
    },
    "Eagle Fleet": {
        "main": {"ship": "Eagle", "count_ratio": 1.0, "role": "DPS"},
        "logi": {"ship": "Scimitar", "count_ratio": 0.2, "role": "Logistics"},
        "tackle": {"ship": "Sabre", "count_ratio": 0.1, "role": "Tackle/Interdictor"},
        "links": {"ship": "Vulture", "count_ratio": 0.03, "role": "Command"},
        "base_dps": 380,
        "engagement": "Long range superiority 80-120km, snipe their logistics",
        "positioning": "Hold grid control at optimal range."
    },
    "Ferox Fleet": {
        "main": {"ship": "Ferox", "count_ratio": 1.0, "role": "DPS"},
        "logi": {"ship": "Osprey", "count_ratio": 0.2, "role": "Logistics"},
        "tackle": {"ship": "Sabre", "count_ratio": 0.1, "role": "Tackle/Interdictor"},
        "links": {"ship": "Vulture", "count_ratio": 0.03, "role": "Command"},
        "base_dps": 400,
        "engagement": "Medium range 40-60km, high tank allows anchoring",
        "positioning": "Anchor on FC, maintain tight formation."
    },
    "Sacrilege Fleet": {
        "main": {"ship": "Sacrilege", "count_ratio": 1.0, "role": "DPS"},
        "logi": {"ship": "Guardian", "count_ratio": 0.2, "role": "Logistics"},
        "tackle": {"ship": "Sabre", "count_ratio": 0.1, "role": "Tackle/Interdictor"},
        "links": {"ship": "Damnation", "count_ratio": 0.03, "role": "Command"},
        "base_dps": 450,
        "engagement": "Close range 20-30km, armor tank beats kinetic",
        "positioning": "Commit to brawl, anchor tight."
    },
    "Nightmare Fleet": {
        "main": {"ship": "Nightmare", "count_ratio": 1.0, "role": "DPS"},
        "logi": {"ship": "Guardian", "count_ratio": 0.15, "role": "Logistics"},
        "tackle": {"ship": "Sabre", "count_ratio": 0.1, "role": "Tackle/Interdictor"},
        "links": {"ship": "Damnation", "count_ratio": 0.03, "role": "Command"},
        "base_dps": 600,
        "engagement": "Long range 70-100km, highest alpha in the game",
        "positioning": "Anchor at range, one-volley targets."
    },
    "Loki Fleet": {
        "main": {"ship": "Loki", "count_ratio": 1.0, "role": "DPS/Web"},
        "logi": {"ship": "Guardian", "count_ratio": 0.15, "role": "Logistics"},
        "tackle": {"ship": "Sabre", "count_ratio": 0.1, "role": "Tackle/Interdictor"},
        "links": {"ship": "Damnation", "count_ratio": 0.03, "role": "Command"},
        "base_dps": 400,
        "engagement": "Web range control 40-60km, paint and volley",
        "positioning": "Control engagement range with webs."
    }
}

# Tank counter strategies
COUNTER_TANK = {
    "shield": {"damage": "EM/Thermal", "resist_hole": "EM"},
    "armor": {"damage": "Explosive/Kinetic", "resist_hole": "Explosive"}
}


# ==============================================================================
# Dynamic DPS Enrichment
# ==============================================================================

async def enrich_doctrine_stats(doctrine_name: str) -> Optional[dict]:
    """Enrich doctrine with real Dogma Engine stats.

    Tries to resolve doctrine_name to a fleet_doctrines ID,
    then fetches real stats. Falls back to KNOWN_DOCTRINES hardcoded values.
    Returns None if doctrine is completely unknown.
    """
    hardcoded = KNOWN_DOCTRINES.get(doctrine_name)

    # Try dynamic enrichment via Doctrine Engine
    # Extract ship name from doctrine name (e.g., "Muninn Fleet" -> "Muninn")
    ship_name = doctrine_name.replace(" Fleet", "").strip()
    doctrine_id = resolve_doctrine_id(ship_name)
    if doctrine_id:
        stats = await get_doctrine_stats(doctrine_id)
        if stats:
            return {
                "avg_dps": stats["dps"],
                "ehp": stats["ehp"],
                "tank": stats["tank_type"],
                "cap_stable": stats["cap_stable"],
                "weapon_dps": stats["weapon_dps"],
                "drone_dps": stats["drone_dps"],
                "source": "dogma",
                # Preserve counter info from hardcoded
                "range": hardcoded["range"] if hardcoded else "medium",
                "weapon": hardcoded["weapon"] if hardcoded else "unknown",
                "counters": hardcoded["counters"] if hardcoded else [],
            }

    # Fallback to hardcoded
    if hardcoded:
        return {**hardcoded, "source": "hardcoded", "ehp": 0}

    return None


def _build_counter_response(doctrine_name: str, count: int, enriched: dict) -> dict:
    """Build counter-fleet response with enriched stats."""
    per_ship_dps = enriched.get("avg_dps", 400)
    return {
        "enemy_doctrine": doctrine_name,
        "enemy_dps_per_ship": per_ship_dps,
        "enemy_total_dps": round(per_ship_dps * count, 1),
        "enemy_ehp": enriched.get("ehp", 0),
        "enemy_tank": enriched.get("tank", "unknown"),
        "dps_source": enriched.get("source", "hardcoded"),
    }


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/counter")
async def get_counter_recommendation(doctrine: DoctrineInput):
    """
    Get counter-fleet recommendation for an enemy doctrine.

    Returns optimal fleet composition, numbers, and engagement advice.
    """
    # Check if we have a known counter
    known = KNOWN_DOCTRINES.get(doctrine.doctrine_name)

    if known and known['counters']:
        counter_name = known['counters'][0]
        counter_comp = COUNTER_COMPOSITIONS.get(counter_name)

        if counter_comp:
            # Calculate required numbers
            ships = []
            total_dps = 0

            # Main DPS
            main = counter_comp['main']
            main_count = int(doctrine.estimated_count * main['count_ratio'])
            ships.append({
                "ship": main['ship'],
                "role": main['role'],
                "count": main_count,
                "dps_per_ship": counter_comp['base_dps']
            })
            total_dps += main_count * counter_comp['base_dps']

            # Logistics
            logi = counter_comp['logi']
            logi_count = max(2, int(main_count * logi['count_ratio']))
            ships.append({
                "ship": logi['ship'],
                "role": logi['role'],
                "count": logi_count,
                "dps_per_ship": 0
            })

            # Tackle
            tackle = counter_comp['tackle']
            tackle_count = max(2, int(main_count * tackle['count_ratio']))
            ships.append({
                "ship": tackle['ship'],
                "role": tackle['role'],
                "count": tackle_count,
                "dps_per_ship": 100
            })

            # Links
            links = counter_comp['links']
            links_count = max(1, int(main_count * links['count_ratio']))
            ships.append({
                "ship": links['ship'],
                "role": links['role'],
                "count": links_count,
                "dps_per_ship": 0
            })

            # Add tank counter advice
            tank_advice = COUNTER_TANK.get(doctrine.tank_type, COUNTER_TANK['shield'])

            engagement = f"{counter_comp['engagement']}. Use {tank_advice['damage']} damage ({tank_advice['resist_hole']} is their resist hole)."

            return {
                "their_doctrine": doctrine.doctrine_name,
                "their_count": doctrine.estimated_count,
                "their_dps": doctrine.avg_dps * doctrine.estimated_count,
                "counter_doctrine": counter_name,
                "composition": ships,
                "total_dps": total_dps,
                "dps_advantage": round(total_dps / (doctrine.avg_dps * doctrine.estimated_count), 2) if doctrine.avg_dps > 0 else 1.0,
                "engagement_advice": engagement,
                "positioning": counter_comp['positioning'],
                "confidence": 0.85,
                "notes": f"Known counter for {doctrine.doctrine_name}"
            }

    # Generic counter recommendation
    return await _generate_generic_counter(doctrine)


async def _generate_generic_counter(doctrine: DoctrineInput) -> dict:
    """Generate a generic counter recommendation."""
    tank_advice = COUNTER_TANK.get(doctrine.tank_type, COUNTER_TANK['shield'])

    # Determine counter ship class
    if doctrine.engagement_range == "long":
        counter_ship = "Cerberus"
        counter_doctrine = "Cerberus Fleet"
        advice = "Use missiles to ignore their tracking. Maintain 80km+ range."
    elif doctrine.engagement_range == "short":
        counter_ship = "Muninn"
        counter_doctrine = "Muninn Fleet"
        advice = "Kite at 60km, use superior range to control engagement."
    else:
        counter_ship = "Eagle"
        counter_doctrine = "Eagle Fleet"
        advice = "Maintain range advantage, snipe logistics first."

    counter_comp = COUNTER_COMPOSITIONS.get(counter_doctrine, COUNTER_COMPOSITIONS['Muninn Fleet'])
    main_count = int(doctrine.estimated_count * 1.0)
    total_dps = main_count * counter_comp['base_dps']

    ships = [
        {"ship": counter_ship, "role": "DPS", "count": main_count, "dps_per_ship": counter_comp['base_dps']},
        {"ship": counter_comp['logi']['ship'], "role": "Logistics", "count": max(2, int(main_count * 0.2)), "dps_per_ship": 0},
        {"ship": "Sabre", "role": "Tackle", "count": max(2, int(main_count * 0.1)), "dps_per_ship": 100}
    ]

    engagement = f"{advice} Use {tank_advice['damage']} damage to exploit their {tank_advice['resist_hole']} resist hole."

    return {
        "their_doctrine": doctrine.doctrine_name,
        "their_count": doctrine.estimated_count,
        "their_dps": doctrine.avg_dps * doctrine.estimated_count,
        "counter_doctrine": counter_doctrine,
        "composition": ships,
        "total_dps": total_dps,
        "dps_advantage": round(total_dps / (doctrine.avg_dps * doctrine.estimated_count), 2) if doctrine.avg_dps > 0 else 1.0,
        "engagement_advice": engagement,
        "positioning": counter_comp['positioning'],
        "confidence": 0.6,
        "notes": "Generic counter based on tank/range analysis"
    }


@router.get("/doctrines")
def list_known_doctrines():
    """List all known doctrines in the database."""
    return {
        "doctrines": [
            {
                "name": name,
                "tank": info['tank'],
                "range": info['range'],
                "avg_dps": info['avg_dps'],
                "weapon": info['weapon'],
                "counters": info['counters'],
                "source": "hardcoded",
            }
            for name, info in KNOWN_DOCTRINES.items()
        ]
    }


@router.get("/compositions")
def list_fleet_compositions():
    """List all available fleet compositions."""
    return {
        "compositions": [
            {
                "name": name,
                "main_ship": comp['main']['ship'],
                "logi": comp['logi']['ship'],
                "base_dps": comp['base_dps'],
                "engagement": comp['engagement'],
                "positioning": comp['positioning']
            }
            for name, comp in COUNTER_COMPOSITIONS.items()
        ]
    }


@router.get("/tank-counters")
def get_tank_counters():
    """Get tank type counter information."""
    return {
        "tank_counters": COUNTER_TANK,
        "advice": {
            "shield": "Shield tanks are weak to EM/Thermal. Focus EM damage.",
            "armor": "Armor tanks are weak to Explosive/Kinetic. Focus Explosive damage."
        }
    }


@router.post("/analyze-zkill")
def analyze_from_zkill(
    alliance_id: int = Query(..., description="Alliance ID to analyze"),
    days: int = Query(7, ge=1, le=30, description="Days to analyze")
):
    """
    Analyze an alliance's recent kills to identify their doctrines.

    Uses cached zkillboard data to determine what they're flying.
    """
    with db_cursor() as cur:
        # Check if we have intel data in military DB
        cur.execute("""
            SELECT ship_type_id, COUNT(*) as uses,
                   AVG(ship_value) as avg_value
            FROM intel_kills
            WHERE alliance_id = %s
              AND kill_time > NOW() - INTERVAL '%s days'
            GROUP BY ship_type_id
            ORDER BY uses DESC
            LIMIT 10
        """, (alliance_id, days))
        rows = cur.fetchall()

    if not rows:
        return {
            "alliance_id": alliance_id,
            "period_days": days,
            "detected_doctrines": [],
            "message": "No kill data found. Sync intel first."
        }

    # Match ships to known doctrines - use SDE DB for invTypes
    detected = []
    for row in rows:
        # Get ship name from SDE
        with sde_cursor() as cur:
            cur.execute("""
                SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s
            """, (row['ship_type_id'],))
            type_row = cur.fetchone()
            ship_name = type_row['typeName'] if type_row else f"Type {row['ship_type_id']}"

        # Try to match to doctrine
        doctrine = None
        for doc_name, info in KNOWN_DOCTRINES.items():
            if ship_name.lower() in doc_name.lower():
                doctrine = doc_name
                break

        detected.append({
            "ship_name": ship_name,
            "ship_type_id": row['ship_type_id'],
            "uses": row['uses'],
            "avg_value": float(row['avg_value']) if row['avg_value'] else 0,
            "matched_doctrine": doctrine
        })

    return {
        "alliance_id": alliance_id,
        "period_days": days,
        "detected_ships": detected,
        "message": "Use /counter endpoint with detected doctrines for counter recommendations"
    }
