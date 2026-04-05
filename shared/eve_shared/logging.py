"""Structured logging with Loki compatibility."""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, service_name: str = "eve-service"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging(
    service_name: str,
    level: str = "INFO",
    format_type: str = "json"
) -> logging.Logger:
    """Configure logging for a service."""

    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    handler = logging.StreamHandler(sys.stdout)

    if format_type == "json":
        handler.setFormatter(JSONFormatter(service_name))
    else:
        handler.setFormatter(logging.Formatter(
            f"%(asctime)s - {service_name} - %(levelname)s - %(message)s"
        ))

    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger."""
    return logging.getLogger(name)
