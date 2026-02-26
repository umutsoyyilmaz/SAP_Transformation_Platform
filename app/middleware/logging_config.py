"""
Structured logging configuration.

- Development: human-readable colored format
- Production: JSON format (log aggregator compatible)
- Log level: controlled via LOG_LEVEL env variable
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production / log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Extra fields from request context
        for key in (
            "method",
            "path",
            "status",
            "duration_ms",
            "remote_addr",
            "request_id",
            "tenant_id",
            "program_id",
            "project_id",
            "event_type",
            "security_code",
        ):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        return json.dumps(log_entry, ensure_ascii=False)


class ReadableFormatter(logging.Formatter):
    """Human-readable colored formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",      # cyan
        "INFO": "\033[32m",       # green
        "WARNING": "\033[33m",    # yellow
        "ERROR": "\033[31m",      # red
        "CRITICAL": "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.now().strftime("%H:%M:%S")
        duration = getattr(record, "duration_ms", None)
        dur_str = f" [{duration:.0f}ms]" if duration is not None else ""
        msg = record.getMessage()
        base = f"{color}{ts} {record.levelname:<8}{self.RESET} {record.name}: {msg}{dur_str}"
        if record.exc_info and record.exc_info[0] is not None:
            base += "\n" + self.formatException(record.exc_info)
        return base


def configure_logging(app):
    """
    Set up structured logging for the Flask app.

    Reads LOG_LEVEL from env (default: DEBUG in dev, INFO in prod).
    Development  → ReadableFormatter on stderr
    Production   → JSONFormatter on stderr
    """
    is_testing = app.config.get("TESTING", False)
    is_prod = not app.config.get("DEBUG", False) and not is_testing

    level_name = os.getenv("LOG_LEVEL", "INFO" if is_prod else "DEBUG")
    level = getattr(logging, level_name.upper(), logging.INFO)

    # Choose formatter
    formatter = JSONFormatter() if is_prod else ReadableFormatter()

    # Root handler (single stream handler to avoid duplication)
    root = logging.getLogger()
    # Remove existing handlers to prevent duplicates in tests
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    root.addHandler(handler)
    root.setLevel(level)

    # Quieten noisy libraries
    for noisy in ("urllib3", "werkzeug", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Flask app logger
    app.logger.setLevel(level)

    if not is_testing:
        app.logger.info("Logging configured: level=%s format=%s",
                        level_name, "JSON" if is_prod else "readable")
