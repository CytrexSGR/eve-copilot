"""Shared helpers for reports package — report types, DB retrieval, ESI name fetching."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from fastapi import HTTPException

from app.database import db_cursor

logger = logging.getLogger(__name__)


# Report types
REPORT_TYPES = [
    'pilot_intelligence',
    'war_profiteering',
    'alliance_wars',
    'trade_routes',
    'war_economy',
    'strategic_briefing',
    'alliance_wars_analysis',
    'war_economy_analysis'
]


def _fetch_alliance_names_from_esi(alliance_ids: List[int], cur) -> Dict[int, str]:
    """Fetch missing alliance names from ESI and store in cache.
    Uses concurrent requests (up to 10 parallel) for ~5x speedup.
    """
    if not alliance_ids:
        return {}

    from concurrent.futures import ThreadPoolExecutor, as_completed

    ids_to_fetch = alliance_ids[:20]
    fetched = {}

    def _fetch_one(alliance_id: int):
        """Fetch a single alliance from ESI. Thread-safe (no shared state)."""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"https://esi.evetech.net/latest/alliances/{alliance_id}/")
                if resp.status_code == 200:
                    data = resp.json()
                    name = data.get('name')
                    ticker = data.get('ticker', '')
                    if name:
                        return (alliance_id, name, ticker)
        except Exception as e:
            logger.warning(f"Failed to fetch alliance {alliance_id} from ESI: {e}")
        return None

    # Fetch in parallel (10 workers)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_one, aid): aid for aid in ids_to_fetch}
        for future in as_completed(futures):
            result = future.result()
            if result:
                alliance_id, name, ticker = result
                fetched[alliance_id] = name
                # DB insert is sequential (cursor not thread-safe)
                cur.execute("""
                    INSERT INTO alliance_name_cache (alliance_id, alliance_name, ticker)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (alliance_id) DO UPDATE SET
                        alliance_name = EXCLUDED.alliance_name,
                        ticker = EXCLUDED.ticker
                """, (alliance_id, name, ticker))
                logger.info(f"Fetched and cached alliance {alliance_id}: {name}")

    return fetched


def get_report(report_type: str) -> Optional[Dict]:
    """
    Get a stored report from the database.
    Returns None if report doesn't exist.
    """
    if report_type not in REPORT_TYPES:
        raise ValueError(f"Unknown report type: {report_type}")

    with db_cursor() as cur:
        cur.execute("""
            SELECT report_data, generated_at
            FROM stored_reports
            WHERE report_type = %s
        """, (report_type,))

        row = cur.fetchone()
        if row:
            report_data = row["report_data"]
            generated_at = row["generated_at"]

            # Add metadata to report
            if isinstance(report_data, dict):
                report_data['_generated_at'] = generated_at.isoformat() if generated_at else None

            return report_data

        return None


def get_report_status() -> Dict:
    """
    Get status of all stored reports.
    Returns info about when each report was last generated.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT report_type, generated_at, generation_time_seconds, version
            FROM stored_reports
            ORDER BY report_type
        """)

        rows = cur.fetchall()

        status = {}
        for row in rows:
            report_type = row["report_type"]
            generated_at = row["generated_at"]
            gen_time = row["generation_time_seconds"]
            version = row["version"]
            age_hours = (datetime.utcnow() - generated_at.replace(tzinfo=None)).total_seconds() / 3600 if generated_at else None

            status[report_type] = {
                'generated_at': generated_at.isoformat() if generated_at else None,
                'age_hours': round(age_hours, 1) if age_hours else None,
                'generation_time_seconds': round(gen_time, 1) if gen_time else None,
                'version': version,
                'stale': age_hours > 7 if age_hours else True  # Stale if older than 7 hours
            }

        # Add missing reports
        for rt in REPORT_TYPES:
            if rt not in status:
                status[rt] = {
                    'generated_at': None,
                    'age_hours': None,
                    'generation_time_seconds': None,
                    'version': 0,
                    'stale': True
                }

        return status


def get_stored_report_or_error(report_type: str) -> Dict:
    """Get a stored report or raise HTTPException if not available."""
    report = get_report(report_type)
    if report is None:
        raise HTTPException(
            status_code=503,
            detail=f"Report '{report_type}' not yet generated. Please wait for the next cron cycle."
        )
    return report
