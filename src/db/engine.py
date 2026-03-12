"""
src/db/engine.py
SQLAlchemy engine and safe query executor — MySQL edition.

Key MySQL differences vs PostgreSQL:
  - Driver  : mysql+pymysql  (pure Python, no system libs)
  - Dialect : MySQL uses backtick identifiers, LIMIT syntax identical
  - Pool    : NullPool avoided; QueuePool with pool_recycle for 8-hr timeout
  - Schema  : information_schema used for live discovery
"""
from __future__ import annotations

from typing import Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError
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
            pool_recycle=3600,      # recycle connections before MySQL's 8-hr timeout
            pool_pre_ping=True,     # cheap SELECT 1 before each connection use
            connect_args={
                "connect_timeout": 10,          # fail fast if host unreachable
                "read_timeout": 30,             # max seconds waiting for query
                "write_timeout": 30,
            },
            echo=(settings.app_env == "development"),
        )
        log.info(
            "db_engine_created",
            host=settings.mysql_host,
            db=settings.mysql_db,
            driver="mysql+pymysql",
        )
    return _engine


def test_connection() -> bool:
    """Return True if the DB is reachable, False otherwise."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


def safe_execute(sql: str, params: dict | None = None) -> dict[str, Any]:
    """
    Execute a pre-validated SELECT query and return structured results.

    Returns:
        {
            "query"    : str,
            "rows"     : list[dict],
            "row_count": int,
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
    """
    Auto-discover live table + column schema from the connected MySQL database.
    Uses SQLAlchemy inspector (wraps information_schema internally).
    """
    engine = get_engine()
    inspector = inspect(engine)
    schema: dict = {}

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        fks = inspector.get_foreign_keys(table_name)
        pk_info = inspector.get_pk_constraint(table_name)
        pk_cols = set(pk_info.get("constrained_columns", []))

        schema[table_name] = {
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "primary_key": col["name"] in pk_cols,
                }
                for col in columns
            ],
            "foreign_keys": [
                {
                    "columns": fk["constrained_columns"],
                    "references": f"{fk['referred_table']}({', '.join(fk['referred_columns'])})",
                }
                for fk in fks
            ],
        }
    return schema


def get_schema_as_ddl() -> str:
    """
    Return a CREATE TABLE DDL string auto-generated from the live DB.
    This is injected into the LLM prompt so Claude always sees the real schema.
    """
    engine = get_engine()
    inspector = inspect(engine)
    lines: list[str] = []

    for table in inspector.get_table_names():
        cols = inspector.get_columns(table)
        pk = set(inspector.get_pk_constraint(table).get("constrained_columns", []))
        fks = {
            fk["constrained_columns"][0]: f"{fk['referred_table']}({fk['referred_columns'][0]})"
            for fk in inspector.get_foreign_keys(table)
            if fk["constrained_columns"]
        }

        col_defs = []
        for c in cols:
            parts = [f"  {c['name']}", str(c["type"])]
            if c["name"] in pk:
                parts.append("PRIMARY KEY")
            if not c.get("nullable", True):
                parts.append("NOT NULL")
            if c["name"] in fks:
                parts.append(f"-- FK -> {fks[c['name']]}")
            col_defs.append(" ".join(parts))

        lines.append(f"CREATE TABLE {table} (\n" + ",\n".join(col_defs) + "\n);")

    return "\n\n".join(lines)