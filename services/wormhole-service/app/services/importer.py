"""Wormhole data importer from external sources."""
import asyncio
import csv
import hashlib
import io
from typing import Optional
import aiohttp

PATHFINDER_BASE = "https://raw.githubusercontent.com/exodus4d/pathfinder/master/export/csv"
STATICS_URL = f"{PATHFINDER_BASE}/system_static.csv"
WORMHOLE_URL = f"{PATHFINDER_BASE}/wormhole.csv"


class WormholeImporter:
    """Import wormhole data from Pathfinder GitHub."""

    def parse_statics_csv(self, content: str) -> list[dict]:
        """Parse system_static.csv: system -> WH type mapping."""
        reader = csv.DictReader(io.StringIO(content), delimiter=';')
        result = []
        for row in reader:
            system_id = row.get('systemId', '').strip()
            type_id = row.get('typeId', '').strip()
            if system_id and type_id:  # Skip rows with missing values
                result.append({
                    'system_id': int(system_id),
                    'type_id': int(type_id)
                })
        return result

    def parse_wormhole_csv(self, content: str) -> list[dict]:
        """Parse wormhole.csv: WH code -> scan strength."""
        reader = csv.DictReader(io.StringIO(content), delimiter=';')
        result = []
        for row in reader:
            strength = row.get('scanWormholeStrength', '').strip()
            result.append({
                'code': row['Name'],  # Note: header is capitalized
                'scan_strength': float(strength) if strength else None
            })
        return result

    def calculate_checksum(self, content: str) -> str:
        """SHA-256 checksum for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def fetch_statics(self) -> tuple[str | None, list[dict]]:
        """Fetch system statics from Pathfinder."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(STATICS_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    content = await resp.text()
                    return self.calculate_checksum(content), self.parse_statics_csv(content)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"[ERROR] Failed to fetch statics: {e}")
            return None, []

    async def fetch_wormholes(self) -> tuple[str | None, list[dict]]:
        """Fetch wormhole scan strengths from Pathfinder."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(WORMHOLE_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    content = await resp.text()
                    return self.calculate_checksum(content), self.parse_wormhole_csv(content)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"[ERROR] Failed to fetch wormholes: {e}")
            return None, []
