"""Snapshot generation using Playwright."""
import asyncio
import hashlib
import json
import logging
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import httpx
from playwright.async_api import async_playwright

from .config import MAPS, SNAPSHOT_DIR, WAR_INTEL_URL

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path(SNAPSHOT_DIR)
SNAPSHOT_PATH.mkdir(parents=True, exist_ok=True)


async def generate_snapshot(
    map_type: str,
    region: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    wait_ms: int = 3000,
    params: Optional[Dict[str, Any]] = None,
) -> dict:
    if map_type not in MAPS:
        raise ValueError(f"Unknown map type: {map_type}")

    map_config = MAPS[map_type]
    url_params = {"snapshot": "true"}
    if region:
        url_params["region"] = region
    if params:
        for key, value in params.items():
            if key in map_config["params"]:
                url_params[key] = str(value).lower() if isinstance(value, bool) else str(value)

    base_url = map_config["url"]
    url = f"{base_url}?{urlencode(url_params)}"
    param_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    snapshot_id = f"{map_type}-{timestamp}-{param_hash}"
    filename = f"{snapshot_id}.png"
    filepath = SNAPSHOT_PATH / filename

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": width, "height": height})
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")

        try:
            await page.wait_for_selector('[data-map-ready="true"]', timeout=30000)
        except Exception:
            await page.wait_for_selector('canvas', timeout=10000)

        await asyncio.sleep(wait_ms / 1000)

        canvas = await page.query_selector("canvas")
        if canvas:
            await canvas.screenshot(path=str(filepath))
        else:
            await page.screenshot(path=str(filepath))

        await browser.close()

    return {
        "snapshot_id": snapshot_id,
        "filename": filename,
        "url": f"/snapshots/{filename}",
        "map_type": map_type,
        "created_at": datetime.utcnow().isoformat(),
        "params": url_params,
    }


async def _fetch_api_data(minutes: int) -> dict:
    """Fetch war data from war-intel-service."""
    hours = max(1, ceil(minutes / 60))
    async with httpx.AsyncClient(base_url=WAR_INTEL_URL, timeout=30.0) as client:
        summary_req = client.get("/api/war/summary", params={"hours": hours})
        conflicts_req = client.get("/api/war/conflicts", params={"minutes": minutes})
        hot_systems_req = client.get("/api/war/hot-systems", params={"minutes": minutes, "limit": 20})

        results = await asyncio.gather(summary_req, conflicts_req, hot_systems_req, return_exceptions=True)

    data = {"war_summary": {}, "conflicts": [], "hot_systems": []}
    keys = ["war_summary", "conflicts", "hot_systems"]
    for key, res in zip(keys, results):
        if isinstance(res, Exception):
            logger.warning("API fetch failed for %s: %s", key, res)
        elif res.status_code == 200:
            body = res.json()
            if key == "conflicts":
                data[key] = body.get("conflicts", [])[:20]
            elif key == "hot_systems":
                data[key] = body if isinstance(body, list) else body.get("systems", body.get("hot_systems", []))
            else:
                data[key] = body
        else:
            logger.warning("API %s returned %d", key, res.status_code)

    return data


async def generate_atomic_snapshot(
    map_type: str = "ectmap",
    minutes: int = 1440,
    region: Optional[str] = None,
    color_mode: str = "security",
    width: int = 1920,
    height: int = 1080,
    wait_ms: int = 5000,
    extra_params: Optional[Dict[str, Any]] = None,
) -> dict:
    """Generate screenshot + API data atomically in parallel."""
    if map_type not in MAPS:
        raise ValueError(f"Unknown map type: {map_type}")

    # Build map params
    map_params = {
        "colorMode": color_mode,
        "killsMinutes": str(minutes),
    }
    if extra_params:
        map_params.update(extra_params)

    # Run screenshot + API fetch in parallel
    screenshot_task = generate_snapshot(
        map_type=map_type,
        region=region,
        width=width,
        height=height,
        wait_ms=wait_ms,
        params=map_params,
    )
    api_task = _fetch_api_data(minutes)

    screenshot_result, api_data = await asyncio.gather(screenshot_task, api_task)

    # Store JSON alongside the PNG
    snapshot_id = screenshot_result["snapshot_id"]
    json_path = SNAPSHOT_PATH / f"{snapshot_id}.json"
    json_payload = {
        "snapshot_id": snapshot_id,
        "minutes": minutes,
        "region": region,
        "color_mode": color_mode,
        "created_at": screenshot_result["created_at"],
        "params": screenshot_result["params"],
        "data": api_data,
    }
    json_path.write_text(json.dumps(json_payload, default=str, ensure_ascii=False))

    return {
        "snapshot_id": snapshot_id,
        "image_url": screenshot_result["url"],
        "data_url": f"/snapshots/{snapshot_id}.json",
        "map_type": map_type,
        "minutes": minutes,
        "region": region,
        "created_at": screenshot_result["created_at"],
        "params": screenshot_result["params"],
        "data": api_data,
    }


def list_snapshots(limit: int = 50) -> list:
    snapshots = []
    for f in sorted(SNAPSHOT_PATH.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        json_file = f.with_suffix(".json")
        snapshots.append({
            "snapshot_id": f.stem,
            "filename": f.name,
            "url": f"/snapshots/{f.name}",
            "map_type": f.stem.split("-")[0] if "-" in f.stem else "unknown",
            "size_bytes": f.stat().st_size,
            "has_data": json_file.exists(),
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return snapshots


def get_snapshot_data(snapshot_id: str) -> Optional[dict]:
    json_path = SNAPSHOT_PATH / f"{snapshot_id}.json"
    if json_path.exists():
        return json.loads(json_path.read_text())
    return None


def delete_snapshot(snapshot_id: str) -> bool:
    filepath = SNAPSHOT_PATH / f"{snapshot_id}.png"
    json_path = SNAPSHOT_PATH / f"{snapshot_id}.json"
    deleted = False
    if filepath.exists():
        filepath.unlink()
        deleted = True
    if json_path.exists():
        json_path.unlink()
    return deleted
