"""
src/core/logger.py
Structured JSON logging via structlog.

Every log line is a JSON object — easy to parse/ship to Datadog, Loki, CloudWatch etc.

Usage:
    from src.core.logger import setup_logging, get_logger

    setup_logging()                    # call once at app startup (src/app.py)
    log = get_logger(__name__)         # one logger per module

    log.info("query_executed", row_count=42, sql_preview="SELECT ...")
    log.warning("cache_miss", key="abc123")
    log.error("db_connection_failed", error=str(exc))

Output format (JSON, one line per event):
    {"level": "info", "timestamp": "2025-03-12T10:00:00Z",
     "event": "query_executed", "row_count": 42, "sql_preview": "SELECT ..."}
"""
import logging
import structlog
from src.core.config import get_settings


def setup_logging() -> None:
    """
    Configure structlog. Call this exactly once at application startup.
    Log level is read from settings.log_level (env var LOG_LEVEL).
    Defaults to INFO if not set or invalid.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Also configure stdlib logging so SQLAlchemy / uvicorn logs
    # flow through the same structlog pipeline
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
    )

    structlog.configure(
        processors=[
            # Merge any context variables bound with structlog.contextvars.bind_contextvars()
            structlog.contextvars.merge_contextvars,
            # Add log level string ("info", "warning", "error" …)
            structlog.processors.add_log_level,
            # ISO-8601 timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Render exception tracebacks if passed via exc_info=True
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            # Final output: one JSON line per event
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,   # small perf win in production
    )


def get_logger(name: str = __name__):
    """
    Return a bound structlog logger for the given module name.

    Example:
        log = get_logger(__name__)
        log.info("pipeline_start", user_query="show all employees")
    """
    return structlog.get_logger(name)