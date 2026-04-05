"""Alliance scraper - rankings and statistics from DOTLAN."""

import logging
import re
import time

from bs4 import BeautifulSoup

from app.services.scraper_base import (
    BaseScraper, dotlan_scrape_total, dotlan_scrape_duration,
    dotlan_rows_scraped, dotlan_data_freshness,
)

logger = logging.getLogger(__name__)


class AllianceScraper(BaseScraper):
    """Scrapes alliance rankings and statistics from DOTLAN."""

    SCRAPER_NAME = "alliance"

    async def scrape_rankings(self) -> int:
        """Scrape alliance ranking table from /alliance page.

        All ~80 alliances with sov are on a single page.
        Returns number of alliances processed.
        """
        url = f"{self.BASE_URL}/alliance"
        html = await self.fetch(url)
        soup = BeautifulSoup(html, "lxml")

        alliances_processed = 0
        rank = 0

        # Find alliance links in the ranking table
        # DOTLAN links: /alliance/Alliance_Name
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                # Look for alliance link
                alliance_link = row.find("a", href=re.compile(r"^/alliance/[^/]+$"))
                if not alliance_link:
                    continue

                try:
                    href = alliance_link.get("href", "")
                    alliance_slug = href.replace("/alliance/", "").strip()
                    alliance_name = alliance_link.get_text(strip=True)

                    if not alliance_name or not alliance_slug:
                        continue

                    rank += 1

                    # Extract numeric values from cells
                    numbers = []
                    for cell in cells:
                        text = cell.get_text(strip=True).replace(",", "")
                        if text.isdigit():
                            numbers.append(int(text))

                    # Expected order: Systems, Members, Corps (may vary)
                    systems_count = numbers[0] if len(numbers) >= 1 else 0
                    member_count = numbers[1] if len(numbers) >= 2 else 0
                    corp_count = numbers[2] if len(numbers) >= 3 else 0

                    # Try to resolve alliance ID from our cache
                    alliance_id = self._resolve_alliance_id(alliance_name)

                    # Insert daily snapshot
                    with self.db.cursor() as cur:
                        cur.execute("""
                            INSERT INTO dotlan_alliance_stats
                                (alliance_name, alliance_slug, alliance_id,
                                 systems_count, member_count, corp_count, rank_by_systems)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (alliance_slug, snapshot_date)
                            DO UPDATE SET
                                alliance_name = EXCLUDED.alliance_name,
                                alliance_id = COALESCE(EXCLUDED.alliance_id, dotlan_alliance_stats.alliance_id),
                                systems_count = EXCLUDED.systems_count,
                                member_count = EXCLUDED.member_count,
                                corp_count = EXCLUDED.corp_count,
                                rank_by_systems = EXCLUDED.rank_by_systems,
                                scraped_at = NOW()
                        """, (alliance_name, alliance_slug, alliance_id,
                              systems_count, member_count, corp_count, rank))

                    alliances_processed += 1

                except Exception as e:
                    logger.error(f"Error parsing alliance row: {e}")

        logger.info(f"Scraped {alliances_processed} alliance rankings")
        return alliances_processed

    def _resolve_alliance_id(self, alliance_name: str) -> int | None:
        """Try to resolve alliance name to ID from alliance_name_cache."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT alliance_id FROM alliance_name_cache
                WHERE alliance_name = %s
                LIMIT 1
            """, (alliance_name,))
            result = cur.fetchone()
            return result["alliance_id"] if result else None

    async def run_ranking_scan(self):
        """Run alliance ranking scrape with logging and metrics."""
        start_time = time.time()
        log_id = self.log_scrape_start(self.SCRAPER_NAME)

        try:
            count = await self.scrape_rankings()
            duration = time.time() - start_time

            self.log_scrape_end(log_id, "success", rows=count, duration=duration)
            dotlan_scrape_total.labels(scraper=self.SCRAPER_NAME, status="success").inc()
            dotlan_scrape_duration.labels(scraper=self.SCRAPER_NAME).observe(duration)
            dotlan_rows_scraped.labels(scraper=self.SCRAPER_NAME).inc(count)
            dotlan_data_freshness.labels(scraper=self.SCRAPER_NAME).set(0)

        except Exception as e:
            duration = time.time() - start_time
            self.log_scrape_end(log_id, "error", error=str(e), duration=duration)
            dotlan_scrape_total.labels(scraper=self.SCRAPER_NAME, status="error").inc()
            raise
