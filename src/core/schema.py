"""
src/core/schema.py
Schema handling for the LLM prompt builder.

Strategy:
  1. On startup (or first request), auto-discover the real schema from MySQL
     using get_schema_as_ddl() from db/engine.py.
  2. Cache it in memory so we don't hit the DB on every request.
  3. Fall back to the static HRMS schema string if DB is unreachable.

This means the LLM always sees YOUR actual CRM tables — not a hardcoded guess.
"""
from __future__ import annotations
import threading
from src.core.logger import get_logger

log = get_logger(__name__)

# ── Thread-safe lazy cache ─────────────────────────────────────────────────────
_schema_cache: str | None = None
_schema_lock = threading.Lock()


# ── Static fallback (used only when DB is unreachable) ────────────────────────
# Replace / extend this with your actual HRMS table structures if needed.
STATIC_FALLBACK_SCHEMA = """
-- ⚠️  Static fallback schema (DB unreachable at startup).
-- Update this block to match your actual crm database tables.

CREATE TABLE employees (
    employee_id       INT PRIMARY KEY,
    first_name        VARCHAR(50),
    last_name         VARCHAR(50),
    email             VARCHAR(150),
    phone             VARCHAR(20),
    hire_date         DATE,
    department_id     INT,   -- FK -> departments(department_id)
    job_title         VARCHAR(100),
    salary            DECIMAL(12,2),
    manager_id        INT,   -- FK -> employees(employee_id)
    employment_status VARCHAR(20)
);

CREATE TABLE departments (
    department_id   INT PRIMARY KEY,
    department_name VARCHAR(100),
    location        VARCHAR(150)
);

CREATE TABLE attendance (
    attendance_id INT PRIMARY KEY,
    employee_id   INT,  -- FK -> employees(employee_id)
    date          DATE,
    check_in      TIME,
    check_out     TIME,
    work_hours    DECIMAL(5,2)
);

CREATE TABLE leave_requests (
    leave_id     INT PRIMARY KEY,
    employee_id  INT,   -- FK -> employees(employee_id)
    leave_type   VARCHAR(50),
    start_date   DATE,
    end_date     DATE,
    leave_status VARCHAR(20)
);

CREATE TABLE payroll (
    payroll_id  INT PRIMARY KEY,
    employee_id INT,   -- FK -> employees(employee_id)
    pay_month   DATE,
    base_salary DECIMAL(12,2),
    bonus       DECIMAL(12,2),
    deductions  DECIMAL(12,2),
    net_salary  DECIMAL(12,2)
);
"""

# ── Dict form for /schema endpoint ────────────────────────────────────────────
# Auto-populated from live DB; static fallback used otherwise.
SCHEMA_DICT: dict = {"tables": [], "source": "unknown"}


def get_live_schema_ddl() -> str:
    """
    Return DDL string from live MySQL DB (cached after first call).
    Falls back to static schema on connection failure.
    """
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache

    with _schema_lock:
        if _schema_cache is not None:   # double-checked locking
            return _schema_cache
        try:
            from src.db.engine import get_schema_as_ddl, discover_schema
            ddl = get_schema_as_ddl()
            if ddl.strip():
                _schema_cache = ddl
                # Also populate SCHEMA_DICT for /schema endpoint
                _populate_schema_dict(discover_schema())
                log.info("schema_loaded_from_db", table_count=ddl.count("CREATE TABLE"))
                return _schema_cache
        except Exception as exc:
            log.warning("schema_discovery_failed_using_fallback", error=str(exc))

        _schema_cache = STATIC_FALLBACK_SCHEMA
        return _schema_cache


def invalidate_schema_cache() -> None:
    """Force re-discovery of schema on next request."""
    global _schema_cache
    with _schema_lock:
        _schema_cache = None
    log.info("schema_cache_invalidated")


def _populate_schema_dict(discovered: dict) -> None:
    tables = []
    for name, info in discovered.items():
        tables.append({
            "name": name,
            "description": "",
            "columns": info["columns"],
            "foreign_keys": info.get("foreign_keys", []),
        })
    SCHEMA_DICT["tables"] = tables
    SCHEMA_DICT["source"] = "live"