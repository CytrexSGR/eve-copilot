"""Sovereignty scraper - campaigns and changes from DOTLAN."""

import logging
import re
import time
from typing import Optional

from bs4 import BeautifulSoup

from app.services.scraper_base import (
    BaseScraper, dotlan_scrape_total, dotlan_scrape_duration,
    dotlan_rows_scraped, dotlan_data_freshness,
)

logger = logging.getLogger(__name__)


class SovereigntyScraper(BaseScraper):
    """Scrapes sovereignty campaigns and changes from DOTLAN."""

    SCRAPER_NAME = "sovereignty"

    async def scrape_campaigns(self) -> int:
        """Scrape active sovereignty campaigns from /sovereignty/campaigns.

        Returns number of campaigns upserted.
        """
        url = f"{self.BASE_URL}/sovereignty/campaigns"
        html = await self.fetch(url)
        soup = BeautifulSoup(html, "lxml")

        campaigns_processed = 0

        # Find campaign table rows
        # DOTLAN campaign rows contain links to /sovereignty/campaign/{id}
        campaign_links = soup.find_all("a", href=re.compile(r"/sovereignty/campaign/\d+"))

        seen_ids = set()
        for link in campaign_links:
            href = link.get("href", "")
            match = re.search(r"/sovereignty/campaign/(\d+)", href)
            if not match:
                continue

            campaign_id = int(match.group(1))
            if campaign_id in seen_ids:
                continue
            seen_ids.add(campaign_id)

            # Navigate up to the table row
            row = link.find_parent("tr")
            if not row:
                continue

            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            # Extract data from cells
            try:
                # Cell structure: Time | Region | System | Action | Defender | Score
                region_name = None
                system_name = None
                structure_type = "IHUB"
                defender_name = None
                score = None

                # Find region link
                region_link = row.find("a", href=re.compile(r"/map/"))
                if region_link:
                    region_name = region_link.get_text(strip=True)

                # Find system link
                system_link = row.find("a", href=re.compile(r"/system/"))
                if system_link:
                    system_name = system_link.get_text(strip=True)

                # Find structure type (IHUB, TCU)
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if text in ("IHUB", "TCU", "STATION"):
                        structure_type = text
                        break

                # Find alliance/defender - there are two alliance links:
                # 1st is the logo img (no text), 2nd has the actual name
                alliance_links = row.find_all("a", href=re.compile(r"/alliance/"))
                for al in alliance_links:
                    name = al.get_text(strip=True)
                    if name:
                        defender_name = name
                        break

                # Find score (percentage in a <span> like "81%")
                score_span = row.find("span", class_=re.compile(r"green|red|yellow"))
                if score_span:
                    score_match = re.search(r"(\d+)%", score_span.get_text(strip=True))
                    if score_match:
                        score = float(score_match.group(1)) / 100.0
                else:
                    # Fallback: search all cells
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        score_match = re.search(r"(\d+)%", text)
                        if score_match:
                            score = float(score_match.group(1)) / 100.0
                            break

                # Resolve IDs
                solar_system_id = self.resolve_system_name_to_id(system_name) if system_name else None
                region_id = self.resolve_region_name_to_id(region_name) if region_name else None

                if not solar_system_id:
                    logger.debug(f"Could not resolve system '{system_name}' for campaign {campaign_id}")
                    continue

                # Resolve defender alliance ID
                defender_id = None
                if defender_name:
                    with self.db.cursor() as cur:
                        cur.execute("""
                            SELECT alliance_id FROM alliance_name_cache
                            WHERE alliance_name = %s
                            LIMIT 1
                        """, (defender_name,))
                        result = cur.fetchone()
                        if result:
                            defender_id = result["alliance_id"]

                # Upsert campaign
                with self.db.cursor() as cur:
                    cur.execute("""
                        INSERT INTO dotlan_sov_campaigns
                            (campaign_id, solar_system_id, region_id, structure_type,
                             defender_name, defender_id, score, status, last_updated)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', NOW())
                        ON CONFLICT (campaign_id)
                        DO UPDATE SET
                            score = EXCLUDED.score,
                            defender_name = EXCLUDED.defender_name,
                            defender_id = EXCLUDED.defender_id,
                            status = 'active',
                            last_updated = NOW()
                    """, (campaign_id, solar_system_id, region_id, structure_type,
                          defender_name, defender_id, score))

                campaigns_processed += 1

            except Exception as e:
                logger.error(f"Error parsing campaign {campaign_id}: {e}")

        # Mark campaigns not seen in this scrape as finished
        if seen_ids:
            with self.db.cursor() as cur:
                cur.execute("""
                    UPDATE dotlan_sov_campaigns
                    SET status = 'finished', last_updated = NOW()
                    WHERE status = 'active'
                      AND campaign_id NOT IN %s
                """, (tuple(seen_ids),))

        logger.info(f"Scraped {campaigns_processed} sovereignty campaigns")
        return campaigns_processed

    async def scrape_changes(self) -> int:
        """Scrape sovereignty changes from /sovereignty/changes.

        Returns number of changes inserted.
        """
        url = f"{self.BASE_URL}/sovereignty/changes"
        html = await self.fetch(url)
        soup = BeautifulSoup(html, "lxml")

        changes_inserted = 0

        # Find change table rows
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                try:
                    # Extract system link
                    system_link = row.find("a", href=re.compile(r"/system/"))
                    if not system_link:
                        continue

                    system_name = system_link.get_text(strip=True)
                    solar_system_id = self.resolve_system_name_to_id(system_name)
                    if not solar_system_id:
                        continue

                    # Extract region
                    region_link = row.find("a", href=re.compile(r"/map/"))
                    region_name = region_link.get_text(strip=True) if region_link else None
                    region_id = self.resolve_region_name_to_id(region_name) if region_name else None

                    # Extract change type
                    change_type = "IHUB"
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if text in ("IHUB", "TCU"):
                            change_type = text
                            break

                    # Extract alliance names (old -> new)
                    alliance_links = row.find_all("a", href=re.compile(r"/alliance/"))
                    old_alliance = alliance_links[0].get_text(strip=True) if len(alliance_links) >= 1 else None
                    new_alliance = alliance_links[1].get_text(strip=True) if len(alliance_links) >= 2 else None

                    # Extract timestamp from first cell
                    timestamp_text = cells[0].get_text(strip=True)
                    changed_at = self._parse_change_timestamp(timestamp_text)
                    if not changed_at:
                        continue

                    # Insert (unique constraint prevents duplicates)
                    with self.db.cursor() as cur:
                        cur.execute("""
                            INSERT INTO dotlan_sov_changes
                                (solar_system_id, region_id, change_type,
                                 old_alliance_name, new_alliance_name, changed_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (solar_system_id, change_type, changed_at) DO NOTHING
                        """, (solar_system_id, region_id, change_type,
                              old_alliance, new_alliance, changed_at))

                    changes_inserted += 1

                except Exception as e:
                    logger.error(f"Error parsing sov change row: {e}")

        logger.info(f"Scraped {changes_inserted} sovereignty changes")
        return changes_inserted

    def _parse_change_timestamp(self, text: str) -> Optional[str]:
        """Parse DOTLAN timestamp text to ISO format."""
        from datetime import datetime

        # DOTLAN uses various date formats
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(text.strip(), fmt)
                return dt.isoformat()
            except ValueError:
                continue
        return None

    async def run_campaign_scan(self):
        """Run campaign scrape with logging and metrics."""
        start_time = time.time()
        log_id = self.log_scrape_start(f"{self.SCRAPER_NAME}_campaigns")

        try:
            count = await self.scrape_campaigns()
            duration = time.time() - start_time

            self.log_scrape_end(log_id, "success", rows=count, duration=duration)
            dotlan_scrape_total.labels(scraper=f"{self.SCRAPER_NAME}_campaigns", status="success").inc()
            dotlan_scrape_duration.labels(scraper=f"{self.SCRAPER_NAME}_campaigns").observe(duration)
            dotlan_rows_scraped.labels(scraper=f"{self.SCRAPER_NAME}_campaigns").inc(count)
            dotlan_data_freshness.labels(scraper=f"{self.SCRAPER_NAME}_campaigns").set(0)

        except Exception as e:
            duration = time.time() - start_time
            self.log_scrape_end(log_id, "error", error=str(e), duration=duration)
            dotlan_scrape_total.labels(scraper=f"{self.SCRAPER_NAME}_campaigns", status="error").inc()
            raise

    async def run_changes_scan(self):
        """Run changes scrape with logging and metrics."""
        start_time = time.time()
        log_id = self.log_scrape_start(f"{self.SCRAPER_NAME}_changes")

        try:
            count = await self.scrape_changes()
            duration = time.time() - start_time

            self.log_scrape_end(log_id, "success", rows=count, duration=duration)
            dotlan_scrape_total.labels(scraper=f"{self.SCRAPER_NAME}_changes", status="success").inc()
            dotlan_scrape_duration.labels(scraper=f"{self.SCRAPER_NAME}_changes").observe(duration)
            dotlan_rows_scraped.labels(scraper=f"{self.SCRAPER_NAME}_changes").inc(count)
            dotlan_data_freshness.labels(scraper=f"{self.SCRAPER_NAME}_changes").set(0)

        except Exception as e:
            duration = time.time() - start_time
            self.log_scrape_end(log_id, "error", error=str(e), duration=duration)
            dotlan_scrape_total.labels(scraper=f"{self.SCRAPER_NAME}_changes", status="error").inc()
            raise
