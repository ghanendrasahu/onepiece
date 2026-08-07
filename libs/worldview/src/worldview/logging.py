"""Structured JSON logging setup (GCP/AWS CloudWatch compatible)."""

import json
import logging
import sys
from typing import Any

from worldview.request_id import RequestIDFilter


class JsonFormatter(logging.Formatter):
    """Emit structured JSON logs with PII-safe fields."""

    _BASE_FIELDS = ("level", "logger", "timestamp", "message")

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self._BASE_FIELDS and not key.startswith("_"):
                entry[key] = value
        return json.dumps(entry, default=str)


def setup_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """Configure root logging to emit JSON lines to stdout."""
    root = logging.getLogger()
    if root.handlers:  # idempotent
        root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIDFilter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logging.getLogger(service_name)
