"""Plain text intelligence summary endpoint."""

import logging
from datetime import datetime

from fastapi import APIRouter, Response

from ._helpers import get_report
from .power_assessment import _build_power_assessment_local

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary/text", response_class=Response)
def get_text_summary():
    """
    Plain Text Intelligence Summary

    Returns a human-readable text summary of current EVE intelligence.
    Designed for AI assistants and text-based clients.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("EVE ONLINE INTELLIGENCE BRIEFING")
    lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("=" * 60)
    lines.append("")

    # Battle Report Summary
    try:
        battle = get_report('pilot_intelligence')
        if battle:
            g = battle.get('global', {})
            lines.append("## 24H BATTLE STATISTICS")
            lines.append(f"Total Kills: {g.get('total_kills', 0):,}")
            lines.append(f"ISK Destroyed: {g.get('total_isk_destroyed', 0) / 1e12:.2f}T")
            lines.append(f"Peak Hour: {g.get('peak_hour_utc', 'N/A')}:00 UTC ({g.get('peak_kills_per_hour', 0):,} kills)")
            lines.append("")

            # Hot Zones
            hot_zones = battle.get('hot_zones', [])[:5]
            if hot_zones:
                lines.append("### Hot Zones (Most Active Systems)")
                for hz in hot_zones:
                    lines.append(f"  - {hz.get('system_name', '?')} ({hz.get('region_name', '?')}): {hz.get('kills', 0)} kills, {hz.get('total_isk_destroyed', 0) / 1e9:.1f}B ISK")
                lines.append("")

            # Capital Kills
            caps = battle.get('capital_kills', {})
            total_caps = sum(c.get('count', 0) for c in caps.values())
            if total_caps > 0:
                lines.append(f"### Capital Ship Losses: {total_caps}")
                for cap_type, data in caps.items():
                    if data.get('count', 0) > 0:
                        lines.append(f"  - {cap_type.replace('_', ' ').title()}: {data['count']} ({data.get('total_isk', 0) / 1e9:.1f}B ISK)")
                lines.append("")
    except Exception as e:
        logger.warning(f"Failed to include battle report: {e}")

    # Power Assessment
    try:
        power = _build_power_assessment_local()
        if power:
            lines.append("## POWER ASSESSMENT (24h)")
            lines.append("")

            gaining = power.get('gaining_power', [])[:5]
            if gaining:
                lines.append("### Gaining Power (Net ISK Positive)")
                for entry in gaining:
                    if isinstance(entry, dict):
                        net_b = entry.get('net_isk', 0) / 1e9
                        lines.append(f"  - {entry.get('name', '?')}: +{net_b:.1f}B net, {entry.get('pilots', 0)} pilots, {entry.get('kills', 0)}K/{entry.get('losses', 0)}L")
                lines.append("")

            losing = power.get('losing_power', [])[:5]
            if losing:
                lines.append("### Losing Power (Net ISK Negative)")
                for entry in losing:
                    if isinstance(entry, dict):
                        net_b = entry.get('net_isk', 0) / 1e9
                        lines.append(f"  - {entry.get('name', '?')}: {net_b:.1f}B net, {entry.get('pilots', 0)} pilots, {entry.get('kills', 0)}K/{entry.get('losses', 0)}L")
                lines.append("")

            isk_eff = power.get('isk_efficiency', [])[:5]
            if isk_eff:
                lines.append("### ISK Efficiency (Best ISK/Pilot)")
                for entry in isk_eff:
                    if isinstance(entry, dict):
                        isk_per = entry.get('isk_per_pilot', 0) / 1e9
                        lines.append(f"  - {entry.get('name', '?')}: {isk_per:.2f}B/pilot, {entry.get('efficiency', 0):.0f}% efficiency")
                lines.append("")
    except Exception as e:
        logger.warning(f"Failed to include power assessment: {e}")

    # Strategic Briefing
    try:
        briefing = get_report('strategic_briefing')
        if briefing:
            lines.append("## STRATEGIC BRIEFING")
            if briefing.get('briefing'):
                lines.append(briefing['briefing'])
                lines.append("")

            highlights = briefing.get('highlights', [])
            if highlights:
                lines.append("### Key Highlights")
                for h in highlights:
                    lines.append(f"  * {h}")
                lines.append("")

            alerts = briefing.get('alerts', [])
            if alerts:
                lines.append("### ALERTS")
                for a in alerts:
                    lines.append(f"  ! {a}")
                lines.append("")
    except Exception as e:
        logger.warning(f"Failed to include strategic briefing: {e}")

    # Alliance Wars
    try:
        wars = get_report('alliance_wars')
        if wars:
            g = wars.get('global', {})
            conflicts = wars.get('conflicts', [])[:3]
            lines.append("## ALLIANCE CONFLICTS")
            lines.append(f"Active Conflicts: {g.get('active_conflicts', 0)}")
            lines.append(f"Alliances Involved: {g.get('total_alliances_involved', 0)}")
            lines.append("")

            if conflicts:
                lines.append("### Top Active Conflicts")
                for c in conflicts:
                    a1, a2 = c.get('alliance_1_name', '?'), c.get('alliance_2_name', '?')
                    lines.append(f"  {a1} vs {a2}")
                    lines.append(f"    - {a1}: {c.get('alliance_1_kills', 0)}K/{c.get('alliance_1_losses', 0)}L, {c.get('alliance_1_efficiency', 0):.0f}% eff")
                    lines.append(f"    - {a2}: {c.get('alliance_2_kills', 0)}K/{c.get('alliance_2_losses', 0)}L, {c.get('alliance_2_efficiency', 0):.0f}% eff")
                    regions = ', '.join(c.get('primary_regions', [])[:3])
                    lines.append(f"    - Regions: {regions}")
                    lines.append("")
    except Exception as e:
        logger.warning(f"Failed to include alliance wars: {e}")

    lines.append("=" * 60)
    lines.append("END OF BRIEFING")
    lines.append("=" * 60)

    text = "\n".join(lines)
    return Response(content=text, media_type="text/plain; charset=utf-8")
