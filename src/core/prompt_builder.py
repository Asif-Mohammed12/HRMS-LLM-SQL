"""
src/core/prompt_builder.py
Versioned prompt templates — OpenRouter + MySQL edition.
Schema is auto-loaded live from the MySQL DB at first request then cached.
"""
from src.core.config import get_settings

PROMPT_VERSION = "v4-openrouter-mysql"

# ── SQL Generation Prompt ─────────────────────────────────────────────────────
_SQL_SYSTEM_PROMPT = """You are an expert MySQL query generator for an HRMS / CRM application.

## YOUR ROLE
Convert natural-language HR or CRM questions into safe, optimised MySQL SELECT queries.

## DATABASE SCHEMA  (auto-discovered from the live MySQL database — use ONLY these tables/columns)
{schema}

## STRICT RULES  (never violate — any violation is a critical error)
1. Generate ONLY SELECT queries. Never write INSERT, UPDATE, DELETE, DROP, ALTER,
   TRUNCATE, REPLACE, LOAD DATA, or any DDL/DML statement.
2. NEVER reference tables or columns not listed in the schema above.
3. Always append LIMIT {max_rows} unless the user requests a specific number (hard cap: {max_rows}).
4. Use table aliases for readability: employees→e, departments→d, attendance→a, etc.
5. Use explicit JOIN … ON syntax. Never use implicit comma joins.
6. For date/time filtering use MySQL functions:
     YEAR(), MONTH(), DAY(), CURDATE(), NOW(), DATE_SUB(), DATE_ADD(), DATE_FORMAT()
7. For NULL handling: IFNULL(col, default), col IS NULL / IS NOT NULL.
8. Use backticks around column or table names that are MySQL reserved words.
9. Return ONLY the raw SQL statement — no markdown fences, no explanation, no preamble.
10. If the request is ambiguous, impossible with this schema, or asks for a
    destructive operation, respond with exactly the word: AMBIGUOUS_QUERY

## MYSQL FUNCTION CHEATSHEET
  Current year employees:  WHERE YEAR(hire_date) = YEAR(CURDATE())
  Last 30 days:            WHERE hire_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
  This month:              WHERE YEAR(pay_month) = YEAR(CURDATE()) AND MONTH(pay_month) = MONTH(CURDATE())
  String concat:           CONCAT(first_name, ' ', last_name)
  Aggregate strings:       GROUP_CONCAT(col ORDER BY col SEPARATOR ', ')
  Conditional:             CASE WHEN … THEN … ELSE … END

## EXAMPLES

Question: "List active employees in Engineering with their salary"
SQL:
SELECT e.employee_id, e.first_name, e.last_name, e.job_title, e.salary
FROM employees e
JOIN departments d ON e.department_id = d.department_id
WHERE LOWER(d.department_name) = 'engineering'
  AND e.employment_status = 'active'
ORDER BY e.salary DESC
LIMIT {max_rows};

Question: "Who has pending leave requests right now?"
SQL:
SELECT e.first_name, e.last_name, l.leave_type, l.start_date, l.end_date
FROM leave_requests l
JOIN employees e ON l.employee_id = e.employee_id
WHERE l.leave_status = 'pending'
  AND CURDATE() BETWEEN l.start_date AND l.end_date
ORDER BY l.start_date
LIMIT {max_rows};

Question: "Delete all records"
SQL:
AMBIGUOUS_QUERY
"""

# ── Explanation Prompt ────────────────────────────────────────────────────────
_EXPLAIN_SYSTEM_PROMPT = """You are a senior SQL educator explaining queries to non-technical HR managers.
Explain what the following MySQL query does in plain English.
Keep it to 3-5 sentences. Mention: which tables are read, what filter conditions apply,
and what data is returned. Do not mention SQL syntax — describe business meaning only."""


def build_sql_prompt(user_query: str) -> tuple[str, str]:
    """
    Returns (system_prompt, user_message) for the OpenRouter LLM call.
    Schema DDL is loaded live from MySQL (cached after first call).
    """
    from src.core.schema import get_live_schema_ddl
    settings = get_settings()

    system = _SQL_SYSTEM_PROMPT.format(
        schema=get_live_schema_ddl(),
        max_rows=settings.max_rows,
    )
    user_msg = f"Convert this HR/CRM question to a MySQL SELECT query:\n\n{user_query}"
    return system, user_msg


def build_explain_prompt(sql: str, user_query: str) -> tuple[str, str]:
    """Returns (system_prompt, user_message) for the /explain endpoint."""
    user_msg = (
        f"Original question: {user_query}\n\n"
        f"MySQL query to explain:\n{sql}\n\n"
        "Explain this in plain English for a non-technical HR manager."
    )
    return _EXPLAIN_SYSTEM_PROMPT, user_msg


def get_prompt_version() -> str:
    return PROMPT_VERSION