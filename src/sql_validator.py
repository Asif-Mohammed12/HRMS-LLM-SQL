"""
src/core/sql_validator.py
Multi-layer SQL safety validation.  Raises ValueError on any violation.
"""
import re
from src.core.logger import get_logger

log = get_logger(__name__)

# Forbidden DDL/DML keywords
FORBIDDEN_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|MERGE|UPSERT|EXEC|EXECUTE|CALL|GRANT|REVOKE|COPY)\b", re.IGNORECASE),
]

# Prevent stacked statements
SEMICOLON_MULTI = re.compile(r";.+", re.DOTALL)

# Prevent comment-based injection tricks
COMMENT_PATTERNS = [
    re.compile(r"--"),
    re.compile(r"/\*.*?\*/", re.DOTALL),
]

# Tables known to the system
KNOWN_TABLES = {"employees", "departments", "attendance", "leave_requests", "payroll"}


def validate_sql(sql: str) -> str:
    """
    Validate and sanitise a generated SQL string.
    Returns the cleaned SQL or raises ValueError.
    """
    if not sql or not sql.strip():
        raise ValueError("Empty SQL query returned by LLM.")

    # Strip markdown code fences the LLM might include
    sql = _strip_code_fences(sql)

    # Must start with SELECT
    stripped = sql.lstrip()
    if not stripped.upper().startswith("SELECT"):
        raise ValueError(
            f"Only SELECT queries are permitted. Got: '{stripped[:30]}...'"
        )

    # Forbid dangerous keywords
    for pattern in FORBIDDEN_PATTERNS:
        match = pattern.search(sql)
        if match:
            raise ValueError(
                f"Forbidden keyword detected: '{match.group()}'. "
                "Only read-only SELECT queries are allowed."
            )

    # Forbid stacked statements (;  followed by more content)
    if SEMICOLON_MULTI.search(sql):
        raise ValueError("Multiple SQL statements are not allowed.")

    # Strip inline comments (safety measure; not outright blocked but cleansed)
    for pattern in COMMENT_PATTERNS:
        sql = pattern.sub("", sql)

    # Warn on unknown table references (soft check — don't block)
    _check_table_references(sql)

    log.info("sql_validated", sql_preview=sql[:120])
    return sql.strip().rstrip(";")  # remove trailing semicolon for SQLAlchemy text()


def _strip_code_fences(sql: str) -> str:
    """Remove ```sql ... ``` or ``` ... ``` wrappers."""
    sql = re.sub(r"^```(?:sql)?\s*", "", sql.strip(), flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql.strip())
    return sql.strip()


def _check_table_references(sql: str) -> None:
    """Log a warning if the LLM references tables outside the schema."""
    # Very naive extraction: look for FROM/JOIN followed by identifiers
    refs = re.findall(
        r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        sql,
        re.IGNORECASE,
    )
    unknown = {r.lower() for r in refs} - KNOWN_TABLES
    if unknown:
        log.warning("unknown_table_references", tables=list(unknown))
