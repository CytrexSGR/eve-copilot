"""Stored report endpoints — pre-generated reports served from PostgreSQL."""

from typing import Dict
from fastapi import APIRouter, Query

from ._helpers import get_stored_report_or_error, get_report_status

router = APIRouter()


@router.get("/battle-24h")
def get_battle_report() -> Dict:
    """
    24-Hour Battle Report - Pilot Intelligence

    Returns actionable combat intelligence from pilot perspective:
    - Hot zones (top systems by activity)
    - Capital kills summary
    - High-value individual kills with gank detection
    - Danger zones for haulers
    - Ship type breakdown
    - Hourly activity timeline

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('pilot_intelligence')


@router.get("/war-profiteering")
def get_war_profiteering(limit: int = Query(default=20, ge=5, le=50)) -> Dict:
    """
    War Profiteering Daily Digest

    Identifies market opportunities based on destroyed items in combat.
    Shows items with highest market value destroyed in last 24 hours.

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('war_profiteering')


@router.get("/alliance-wars")
def get_alliance_wars() -> Dict:
    """
    Alliance War Tracker

    Tracks active alliance conflicts with kill/death ratios and ISK efficiency.
    Shows top 5 most active alliance wars in last 24 hours.
    Includes auto-detected coalitions based on combat patterns.

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('alliance_wars')


@router.get("/alliance-wars/analysis")
def get_alliance_wars_analysis() -> Dict:
    """
    AI-Powered Alliance Wars Analysis

    Returns an LLM-generated strategic analysis of the current alliance warfare situation.
    Includes a summary and key insights based on the last 24 hours of combat data.

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('alliance_wars_analysis')


@router.get("/war-economy")
def get_war_economy(limit: int = Query(default=10, ge=5, le=20)) -> Dict:
    """
    War Economy Intelligence Report

    Combines combat data with market intelligence to show:
    - Regional Demand: Where combat is happening -> where market demand rises
    - Hot Items: Top destroyed items with market prices
    - Fleet Compositions: Ship class breakdown by region (doctrine detection)
    - Market Opportunities: Items with highest demand from combat

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('war_economy')


@router.get("/war-economy/analysis")
def get_war_economy_analysis_endpoint() -> Dict:
    """
    AI-Powered War Economy Analysis

    Returns an LLM-generated analysis of war economy trends and trading opportunities.
    Includes a summary, insights, recommendations, doctrine alerts, and risk warnings.

    Pre-generated every 6 hours.
    """
    return get_stored_report_or_error('war_economy_analysis')


@router.get("/status")
def get_reports_status() -> Dict:
    """
    Reports Generation Status

    Shows when each report was last generated and if any are stale.
    """
    return {
        "reports": get_report_status(),
        "generation_interval": "6 hours"
    }
