"""
src/db/engine.py
SQLAlchemy engine, session factory, and safe query executor.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from src.core.config import get_settings
from src.core.logger import get_logger

log = get_logger(__name__)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # recycle stale connections
            echo=(settings.app_env == "development"),
        )
        log.info("db_engine_created", url=f"postgresql://{settings.postgres_host}/{settings.postgres_db}")
    return _engine


def safe_execute(sql: str, params: dict | None = None) -> dict[str, Any]:
    """
    Execute a pre-validated SELECT query and return structured results.

    Returns:
        {
            "query": str,
            "rows": list[dict],
            "row_count": int
        }
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            keys = list(result.keys())
            rows = [dict(zip(keys, row)) for row in result.fetchall()]
            log.info("query_executed", row_count=len(rows), sql_preview=sql[:120])
            return {
                "query": sql,
                "rows": rows,
                "row_count": len(rows),
            }
    except SQLAlchemyError as exc:
        log.error("db_execution_error", error=str(exc), sql=sql[:200])
        raise RuntimeError(f"Database execution error: {exc}") from exc


def discover_schema() -> dict:
    """Auto-discover live table schema from the connected database."""
    engine = get_engine()
    inspector = inspect(engine)
    schema = {}
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        fks = inspector.get_foreign_keys(table_name)
        schema[table_name] = {
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                }
                for col in columns
            ],
            "foreign_keys": [
                {
                    "column": fk["constrained_columns"],
                    "references": f"{fk['referred_table']}.{fk['referred_columns']}",
                }
                for fk in fks
            ],
        }
    return schema
