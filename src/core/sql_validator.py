"""
src/core/sql_validator.py
Multi-layer SQL safety validation — MySQL edition.
Raises ValueError on any violation.
"""
import re
from src.core.logger import get_logger

log = get_logger(__name__)

# Forbidden DDL/DML keywords (MySQL-specific additions included)
FORBIDDEN_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|MERGE|"
        r"UPSERT|EXEC|EXECUTE|CALL|GRANT|REVOKE|LOAD\s+DATA|"
        r"INTO\s+OUTFILE|INTO\s+DUMPFILE)\b",
        re.IGNORECASE,
    ),
]

# Stacked statements via semicolon
SEMICOLON_MULTI = re.compile(r";.+", re.DOTALL)

# Comment patterns used for injection tricks
COMMENT_PATTERNS = [
    re.compile(r"--[^\n]*"),         # inline --comment
    re.compile(r"#[^\n]*"),          # MySQL # comment
    re.compile(r"/\*.*?\*/", re.DOTALL),
]

# MySQL information_schema / sys tables — never allow direct access
FORBIDDEN_TABLES = re.compile(
    r"\b(information_schema|performance_schema|mysql|sys)\b",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> str:
    """
    Validate and sanitise generated SQL.
    Returns cleaned SQL string, or raises ValueError.
    """
    if not sql or not sql.strip():
        raise ValueError("Empty SQL query returned by LLM.")

    # Strip markdown code fences the LLM might wrap around SQL
    sql = _strip_code_fences(sql)

    # Must start with SELECT
    if not sql.lstrip().upper().startswith("SELECT"):
        raise ValueError(
            f"Only SELECT queries are permitted. Got: '{sql.lstrip()[:40]}...'"
        )

    # Forbidden DML / DDL keywords
    for pattern in FORBIDDEN_PATTERNS:
        m = pattern.search(sql)
        if m:
            raise ValueError(
                f"Forbidden keyword detected: '{m.group()}'. "
                "Only read-only SELECT queries are allowed."
            )

    # Forbidden system schemas
    m = FORBIDDEN_TABLES.search(sql)
    if m:
        raise ValueError(
            f"Access to system schema '{m.group()}' is not permitted."
        )

    # Stacked statements
    if SEMICOLON_MULTI.search(sql):
        raise ValueError("Multiple SQL statements in one query are not allowed.")

    # Strip comments (cleanse, don't hard-block — LLM sometimes adds them)
    for pattern in COMMENT_PATTERNS:
        sql = pattern.sub("", sql)

    log.info("sql_validated", sql_preview=sql[:120])
    return sql.strip().rstrip(";")   # remove trailing semicolon for SQLAlchemy text()


def _strip_code_fences(sql: str) -> str:
    """Remove ```sql … ``` or ``` … ``` wrappers."""
    sql = re.sub(r"^```(?:sql)?\s*", "", sql.strip(), flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql.strip())
    return sql.strip()