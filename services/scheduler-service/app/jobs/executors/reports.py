"""Report generation executor functions."""

import logging

from ._helpers import _run_python_script

logger = logging.getLogger(__name__)

__all__ = [
    "run_telegram_report",
    "run_alliance_wars",
    "run_war_profiteering",
    "run_report_generator",
]


def run_telegram_report():
    """Execute Telegram battle report."""
    logger.info("Starting telegram_report job")
    return _run_python_script("report_generator.py", timeout=180)


def run_alliance_wars():
    """Execute alliance wars analyzer."""
    logger.info("Starting alliance_wars job")
    # This may need a specific script or use report_generator with params
    return _run_python_script("report_generator.py", timeout=180)


def run_war_profiteering():
    """Execute war profiteering analyzer."""
    logger.info("Starting war_profiteering job")
    return _run_python_script("report_generator.py", timeout=300)


def run_report_generator():
    """Execute intelligence report generator."""
    logger.info("Starting report_generator job")
    return _run_python_script("report_generator.py", timeout=600)
