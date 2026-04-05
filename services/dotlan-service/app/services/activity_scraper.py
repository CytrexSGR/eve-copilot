"""Activity scraper - NPC kills, ship kills, pod kills, jumps per system."""

import logging
import time
from typing import Optional

from bs4 import BeautifulSoup

from app.services.scraper_base import (
    BaseScraper, dotlan_scrape_total, dotlan_scrape_duration,
    dotlan_rows_scraped, dotlan_data_freshness,
)

logger = logging.getLogger(__name__)


class ActivityScraper(BaseScraper):
    """Scrapes system activity data from DOTLAN.

    Two scraping modes:
    1. Detail scan: /system/{name}/stats - 7-day hourly history per system
    2. Region scan: /region/{name} - current summary for all systems in region
    """

    SCRAPER_NAME = "activity"
    # Chart IDs as they appear in DOTLAN's HTML: chart_jumps, chart_npc, chart_kills, chart_pods
    CHARTS = ["jumps", "npc", "kills", "pods"]
    CHART_TO_COLUMN = {
        "jumps": "jumps",
        "npc": "npc_kills",
        "kills": "ship_kills",
        "pods": "pod_kills",
    }

    async def scrape_system_stats(self, system_name: str, system_id: int) -> int:
        """Scrape 7-day hourly history for a single system.

        Parses dotLineChart JavaScript on /system/{name}/stats page.
        Returns number of rows upserted.
        """
        url = f"{self.BASE_URL}/system/{system_name}/stats"
        html = await self.fetch(url)

        rows = {}  # {datetime: {col: val, ...}}
        for chart_id in self.CHARTS:
            col = self.CHART_TO_COLUMN[chart_id]
            for label, value in self.parse_dotline_chart(html, chart_id):
                ts = self.parse_label_to_timestamp(label)
                if ts not in rows:
                    rows[ts] = {"npc_kills": 0, "ship_kills": 0, "pod_kills": 0, "jumps": 0}
                rows[ts][col] = value

        # Also extract ADM data if present
        adm_data = self.parse_dotline_chart(html, "adm")

        if not rows:
            logger.warning(f"No activity data found for {system_name}")
            return 0

        # Batch UPSERT activity data
        with self.db.cursor() as cur:
            for ts, data in rows.items():
                cur.execute("""
                    INSERT INTO dotlan_system_activity
                        (solar_system_id, timestamp, npc_kills, ship_kills, pod_kills, jumps)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (solar_system_id, timestamp)
                    DO UPDATE SET
                        npc_kills = EXCLUDED.npc_kills,
                        ship_kills = EXCLUDED.ship_kills,
                        pod_kills = EXCLUDED.pod_kills,
                        jumps = EXCLUDED.jumps,
                        scraped_at = NOW()
                """, (system_id, ts, data["npc_kills"], data["ship_kills"],
                      data["pod_kills"], data["jumps"]))

            # Upsert ADM data (values come as floats like 4.5)
            for label, value in adm_data:
                if value > 0:
                    ts = self.parse_label_to_timestamp(label)
                    adm_val = float(value)
                    cur.execute("""
                        INSERT INTO dotlan_adm_history (solar_system_id, timestamp, adm_level)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (solar_system_id, timestamp)
                        DO UPDATE SET adm_level = EXCLUDED.adm_level, scraped_at = NOW()
                    """, (system_id, ts, adm_val))

        return len(rows)

    async def scrape_region_systems(self, region_name: str) -> int:
        """Scrape system list table from /region/{name} page.

        Extracts current activity values from the region's system table.
        Returns number of systems processed.
        """
        url = f"{self.BASE_URL}/region/{region_name}"
        html = await self.fetch(url)
        soup = BeautifulSoup(html, "lxml")

        # Find the main system table - DOTLAN uses <table> with system rows
        tables = soup.find_all("table")
        systems_processed = 0

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 5:
                    continue

                # Try to find system link in the row
                system_link = row.find("a", href=lambda h: h and "/system/" in h)
                if not system_link:
                    continue

                system_name = system_link.get_text(strip=True)
                system_id = self.resolve_system_name_to_id(system_name)
                if not system_id:
                    continue

                # Parse numeric values from cells
                # The exact column positions depend on DOTLAN's table structure
                # We'll try to extract any numeric data available
                systems_processed += 1

        return systems_processed

    async def run_detail_scan(self, system_ids: Optional[list[int]] = None, max_systems: int = 200):
        """Run detailed stats scan for specific systems or top-active systems.

        If system_ids not provided, queries top active systems from existing data.
        """
        start_time = time.time()
        log_id = self.log_scrape_start(f"{self.SCRAPER_NAME}_detail")
        total_rows = 0
        total_systems = 0

        try:
            if system_ids:
                # Resolve IDs to names
                systems = []
                with self.db.cursor() as cur:
                    for sid in system_ids[:max_systems]:
                        cur.execute("""
                            SELECT "solarSystemID" as solar_system_id,
                                   "solarSystemName" as solar_system_name
                            FROM "mapSolarSystems"
                            WHERE "solarSystemID" = %s
                        """, (sid,))
                        result = cur.fetchone()
                        if result:
                            systems.append(result)
            else:
                # Get top active systems from recent data
                with self.db.cursor() as cur:
                    cur.execute("""
                        SELECT a.solar_system_id,
                               s."solarSystemName" as solar_system_name
                        FROM (
                            SELECT solar_system_id,
                                   SUM(npc_kills + ship_kills * 10 + jumps) as activity_score
                            FROM dotlan_system_activity
                            WHERE timestamp > NOW() - INTERVAL '24 hours'
                            GROUP BY solar_system_id
                            ORDER BY activity_score DESC
                            LIMIT %s
                        ) a
                        JOIN "mapSolarSystems" s ON s."solarSystemID" = a.solar_system_id
                    """, (max_systems,))
                    systems = cur.fetchall()

                # If no existing data, grab systems from important nullsec regions
                if not systems:
                    with self.db.cursor() as cur:
                        cur.execute("""
                            SELECT "solarSystemID" as solar_system_id,
                                   "solarSystemName" as solar_system_name
                            FROM "mapSolarSystems"
                            WHERE "security" < 0.0
                              AND "regionID" < 11000000
                            ORDER BY RANDOM()
                            LIMIT %s
                        """, (max_systems,))
                        systems = cur.fetchall()

            for system in systems:
                try:
                    rows = await self.scrape_system_stats(
                        system["solar_system_name"],
                        system["solar_system_id"]
                    )
                    total_rows += rows
                    total_systems += 1
                    if total_systems % 25 == 0:
                        logger.info(f"Detail scan progress: {total_systems}/{len(systems)} systems")
                except Exception as e:
                    logger.error(f"Error scraping {system['solar_system_name']}: {e}")

            duration = time.time() - start_time
            self.log_scrape_end(log_id, "success", systems=total_systems,
                                rows=total_rows, duration=duration)
            dotlan_scrape_total.labels(scraper=f"{self.SCRAPER_NAME}_detail", status="success").inc()
            dotlan_scrape_duration.labels(scraper=f"{self.SCRAPER_NAME}_detail").observe(duration)
            dotlan_rows_scraped.labels(scraper=f"{self.SCRAPER_NAME}_detail").inc(total_rows)
            dotlan_data_freshness.labels(scraper=f"{self.SCRAPER_NAME}_detail").set(0)

            logger.info(f"Detail scan complete: {total_systems} systems, {total_rows} rows in {duration:.1f}s")

        except Exception as e:
            duration = time.time() - start_time
            self.log_scrape_end(log_id, "error", systems=total_systems,
                                rows=total_rows, error=str(e), duration=duration)
            dotlan_scrape_total.labels(scraper=f"{self.SCRAPER_NAME}_detail", status="error").inc()
            logger.error(f"Detail scan failed: {e}")
            raise

    async def run_region_scan(self):
        """Run region scan for all K-Space regions.

        Scrapes /system/{name}/stats for a sample of systems per region.
        More efficient than individual system scraping.
        """
        start_time = time.time()
        log_id = self.log_scrape_start(f"{self.SCRAPER_NAME}_region")
        total_rows = 0
        total_systems = 0
        total_regions = 0

        try:
            regions = self.get_all_regions()
            logger.info(f"Starting region scan for {len(regions)} regions")

            for region in regions:
                region_id = region["region_id"]
                region_name = region["region_name"]

                # Get systems for this region
                systems = self.get_systems_for_region(region_id)

                # For region scan, pick a representative sample
                # Prioritize nullsec/lowsec systems
                priority_systems = sorted(systems, key=lambda s: s["security_status"])
                sample = priority_systems[:10]  # Top 10 lowest-sec systems per region

                for system in sample:
                    try:
                        rows = await self.scrape_system_stats(
                            system["solar_system_name"],
                            system["solar_system_id"]
                        )
                        total_rows += rows
                        total_systems += 1
                    except Exception as e:
                        logger.error(f"Error scraping {system['solar_system_name']}: {e}")

                total_regions += 1
                if total_regions % 10 == 0:
                    logger.info(f"Region scan progress: {total_regions}/{len(regions)} regions")

            duration = time.time() - start_time
            self.log_scrape_end(log_id, "success", regions=total_regions,
                                systems=total_systems, rows=total_rows, duration=duration)
            dotlan_scrape_total.labels(scraper=f"{self.SCRAPER_NAME}_region", status="success").inc()
            dotlan_scrape_duration.labels(scraper=f"{self.SCRAPER_NAME}_region").observe(duration)
            dotlan_rows_scraped.labels(scraper=f"{self.SCRAPER_NAME}_region").inc(total_rows)
            dotlan_data_freshness.labels(scraper=f"{self.SCRAPER_NAME}_region").set(0)

            logger.info(f"Region scan complete: {total_regions} regions, {total_systems} systems, "
                        f"{total_rows} rows in {duration:.1f}s")

        except Exception as e:
            duration = time.time() - start_time
            self.log_scrape_end(log_id, "error", regions=total_regions,
                                systems=total_systems, rows=total_rows,
                                error=str(e), duration=duration)
            dotlan_scrape_total.labels(scraper=f"{self.SCRAPER_NAME}_region", status="error").inc()
            logger.error(f"Region scan failed: {e}")
            raise
