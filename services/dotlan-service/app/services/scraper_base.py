"""Base scraper class with HTTP client, rate limiting, retry logic, and DOTLAN parsers."""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Optional

import httpx
from prometheus_client import Counter, Histogram, Gauge

from app.config import settings
from app.database import DatabasePool
from app.services.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# Prometheus metrics
dotlan_scrape_total = Counter(
    "dotlan_scrape_total", "Total scrape operations",
    ["scraper", "status"]
)
dotlan_scrape_duration = Histogram(
    "dotlan_scrape_duration_seconds", "Scrape operation duration",
    ["scraper"]
)
dotlan_rows_scraped = Counter(
    "dotlan_rows_scraped_total", "Total rows scraped and stored",
    ["scraper"]
)
dotlan_http_requests = Counter(
    "dotlan_http_requests_total", "Total HTTP requests to DOTLAN",
    ["status"]
)
dotlan_data_freshness = Gauge(
    "dotlan_data_freshness_hours", "Hours since last successful scrape",
    ["scraper"]
)

# Module-level infrastructure
_rate_limiter: Optional[TokenBucketRateLimiter] = None
_db: Optional[DatabasePool] = None
_http_client: Optional[httpx.AsyncClient] = None


def init_scraper_infrastructure(db: DatabasePool):
    """Initialize shared scraper infrastructure (called from lifespan)."""
    global _rate_limiter, _db, _http_client
    _db = db
    _rate_limiter = TokenBucketRateLimiter(
        rate=settings.dotlan_rate_limit,
        burst=settings.dotlan_rate_burst,
    )
    _http_client = httpx.AsyncClient(
        headers={"User-Agent": settings.dotlan_user_agent},
        timeout=httpx.Timeout(settings.dotlan_request_timeout),
        follow_redirects=True,
    )


async def shutdown_scraper_infrastructure():
    """Shutdown shared scraper infrastructure."""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None


def get_rate_limiter() -> TokenBucketRateLimiter:
    if _rate_limiter is None:
        raise RuntimeError("Scraper infrastructure not initialized")
    return _rate_limiter


def get_db() -> DatabasePool:
    if _db is None:
        raise RuntimeError("Scraper infrastructure not initialized")
    return _db


def get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("Scraper infrastructure not initialized")
    return _http_client


class BaseScraper:
    """Base class for all DOTLAN scrapers."""

    BASE_URL = settings.dotlan_base_url
    MAX_RETRIES = settings.dotlan_max_retries
    INITIAL_BACKOFF = settings.dotlan_initial_backoff
    MAX_BACKOFF = settings.dotlan_max_backoff

    def __init__(self):
        self.db = get_db()
        self.rate_limiter = get_rate_limiter()
        self.client = get_http_client()

    async def fetch(self, url: str) -> str:
        """HTTP GET with rate limiting and retry logic."""
        await self.rate_limiter.acquire()

        backoff = self.INITIAL_BACKOFF
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.client.get(url)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff))
                    logger.warning(f"Rate limited by DOTLAN, waiting {retry_after}s")
                    dotlan_http_requests.labels(status="429").inc()
                    await asyncio.sleep(retry_after)
                    backoff = min(backoff * 2, self.MAX_BACKOFF)
                    continue

                response.raise_for_status()
                dotlan_http_requests.labels(status=str(response.status_code)).inc()
                return response.text

            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                dotlan_http_requests.labels(status="timeout").inc()
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.MAX_BACKOFF)

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP {e.response.status_code} fetching {url}")
                dotlan_http_requests.labels(status=str(e.response.status_code)).inc()
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.MAX_BACKOFF)

        raise RuntimeError(f"Failed after {self.MAX_RETRIES} retries: {url}")

    def parse_dotline_chart(self, html: str, chart_id: str) -> list[tuple[str, int | float]]:
        """Extract data from dotLineChart JavaScript initialization.

        DOTLAN embeds chart data as JS (NOT valid JSON - unquoted keys):
            window.chart_X = new dotLineChart(
                "#chart_X",
                {
                    labels: ["2026-01-28 12", ...],
                    datasets: [{"label":"Jumps","data":[null,"4","17",...]}]
                }
            );

        Returns list of (label, value) tuples.
        """
        # Find the start of the chart data using the constructor call
        marker = f'new dotLineChart(\n\t"#chart_{chart_id}",'
        start_idx = html.find(marker)
        if start_idx == -1:
            # Try without specific whitespace
            marker = f'"#chart_{chart_id}"'
            start_idx = html.find(marker)
            if start_idx == -1:
                logger.debug(f"Chart '{chart_id}' not found in page")
                return []

        # Find the opening brace of the data object after the chart ID string
        brace_start = html.find("{", start_idx + len(marker))
        if brace_start == -1:
            return []

        # Use brace counting to find the matching closing brace
        depth = 0
        brace_end = brace_start
        for i in range(brace_start, len(html)):
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break

        raw_js = html[brace_start:brace_end + 1]

        # Convert JS object to valid JSON: add quotes around unquoted keys
        # Matches keys like `labels:` or `datasets:` at the start of lines/after whitespace
        raw_json = re.sub(r'(?<=[{,\n])\s*(\w+)\s*:', r' "\1":', raw_js)

        try:
            data_obj = json.loads(raw_json)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse chart '{chart_id}' JSON: {e}")
            logger.debug(f"Raw JS snippet (first 200 chars): {raw_js[:200]}")
            return []

        labels = data_obj.get("labels", [])
        datasets = data_obj.get("datasets", [])
        if not datasets:
            return []

        values = datasets[0].get("data", [])

        result = []
        for label, val in zip(labels, values):
            if val is None or val == "null" or val == "":
                parsed_val = 0
            elif isinstance(val, str):
                try:
                    parsed_val = float(val)
                    # Keep as int if it's a whole number
                    if parsed_val == int(parsed_val):
                        parsed_val = int(parsed_val)
                except (ValueError, TypeError):
                    parsed_val = 0
            elif isinstance(val, (int, float)):
                parsed_val = val
            else:
                parsed_val = 0
            result.append((label, parsed_val))

        return result

    @staticmethod
    def parse_label_to_timestamp(label: str) -> datetime:
        """Parse DOTLAN chart label to datetime.

        Labels are in format "YYYY-MM-DD HH" (e.g., "2026-01-28 12").
        """
        return datetime.strptime(label.strip(), "%Y-%m-%d %H")

    def log_scrape_start(self, scraper_name: str) -> int:
        """Log scrape start to database. Returns log entry ID."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO dotlan_scraper_log (scraper_name, started_at, status)
                VALUES (%s, NOW(), 'running')
                RETURNING id
            """, (scraper_name,))
            return cur.fetchone()["id"]

    def log_scrape_end(self, log_id: int, status: str, regions: int = 0,
                       systems: int = 0, rows: int = 0, error: str = None,
                       duration: float = None):
        """Log scrape completion to database."""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE dotlan_scraper_log
                SET finished_at = NOW(), status = %s, regions_scraped = %s,
                    systems_scraped = %s, rows_inserted = %s, error_message = %s,
                    duration_seconds = %s
                WHERE id = %s
            """, (status, regions, systems, rows, error, duration, log_id))

    def get_all_regions(self) -> list[dict]:
        """Get all K-Space regions from SDE.

        Returns list of {region_id, region_name} dicts.
        Excludes wormhole space (regionID >= 11000000) and abyssal.
        """
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT "regionID" as region_id, "regionName" as region_name
                FROM "mapRegions"
                WHERE "regionID" < 11000000
                ORDER BY "regionName"
            """)
            regions = cur.fetchall()

        # Apply region filter if configured
        region_filter = settings.region_filter
        if region_filter:
            regions = [r for r in regions if r["region_name"] in region_filter]

        return regions

    def get_systems_for_region(self, region_id: int) -> list[dict]:
        """Get all solar systems for a region from SDE."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT "solarSystemID" as solar_system_id,
                       "solarSystemName" as solar_system_name,
                       "security" as security_status
                FROM "mapSolarSystems"
                WHERE "regionID" = %s
                ORDER BY "solarSystemName"
            """, (region_id,))
            return cur.fetchall()

    def resolve_system_name_to_id(self, system_name: str) -> Optional[int]:
        """Resolve a system name to its ID from SDE."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT "solarSystemID" as solar_system_id
                FROM "mapSolarSystems"
                WHERE "solarSystemName" = %s
            """, (system_name,))
            result = cur.fetchone()
            return result["solar_system_id"] if result else None

    def resolve_region_name_to_id(self, region_name: str) -> Optional[int]:
        """Resolve a region name to its ID from SDE."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT "regionID" as region_id
                FROM "mapRegions"
                WHERE "regionName" = %s
            """, (region_name,))
            result = cur.fetchone()
            return result["region_id"] if result else None
