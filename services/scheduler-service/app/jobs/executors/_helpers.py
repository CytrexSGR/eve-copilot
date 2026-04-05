"""Shared helpers and constants for scheduler executors."""

import logging
import os
import subprocess
import sys
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Base path for legacy job scripts (configurable via JOBS_PATH env var)
JOBS_PATH = Path(settings.jobs_path)


def _run_python_script(script_name: str, timeout: int = 300) -> bool:
    """Run a Python script as a subprocess.

    Args:
        script_name: Name of the script file (without path)
        timeout: Timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    script_path = JOBS_PATH / script_name

    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(JOBS_PATH.parent)
        )

        if result.returncode == 0:
            logger.info(f"Script completed successfully: {script_name}")
            if result.stdout:
                logger.debug(f"Output: {result.stdout[:500]}")
            return True
        else:
            logger.error(f"Script failed: {script_name}")
            logger.error(f"Exit code: {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr[:500]}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Script timed out: {script_name}")
        return False
    except Exception as e:
        logger.exception(f"Failed to run script: {script_name}")
        return False


def _call_service(url: str, timeout: int = 120, method: str = "post") -> dict:
    """Call a service internal endpoint and return JSON response.

    Args:
        url: Full URL including path (e.g. http://service:8000/api/internal/job)
        timeout: Timeout in seconds
        method: HTTP method (post, get)

    Returns:
        Response JSON as dict

    Raises:
        httpx.HTTPStatusError: If response status >= 400
        Exception: On connection/timeout errors
    """
    import httpx
    resp = getattr(httpx, method)(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _trigger_dotlan_scrape(scraper_name: str, timeout: int = 600) -> bool:
    """Trigger a DOTLAN scrape via HTTP POST to dotlan-service."""
    import httpx
    dotlan_url = os.environ.get('DOTLAN_SERVICE_URL', 'http://dotlan-service:8000')
    try:
        response = httpx.post(
            f"{dotlan_url}/api/dotlan/status/trigger/{scraper_name}",
            timeout=timeout,
        )
        if response.status_code == 200:
            data = response.json()
            logger.info(f"DOTLAN {scraper_name}: {data.get('status', 'unknown')}")
            return True
        else:
            logger.error(f"DOTLAN {scraper_name} failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        logger.exception(f"DOTLAN {scraper_name} trigger failed: {e}")
        return False
