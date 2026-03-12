"""
src/core/prompt_builder.py
Versioned prompt templates — OpenRouter + MySQL edition.
Schema is auto-loaded live from the MySQL DB at first request then cached.
"""
from src.core.config import get_settings

PROMPT_VERSION = "v4-openrouter-mysql"

# ── SQL Generation Prompt ─────────────────────────────────────────────────────
_SQL_SYSTEM_PROMPT = """You are a senior MySQL query engineer generating SQL for a production HRMS / Workforce Management platform.

Your job is to convert natural-language HR or workforce analytics questions into SAFE, optimized MySQL SELECT queries.

The database schema below was automatically extracted from the production database.

──────────────── DATABASE SCHEMA ────────────────
{schema}
─────────────────────────────────────────────────

IMPORTANT: This is a large HR / Attendance / Payroll system.

Main functional modules include:

ACCESS CONTROL
  acc_* tables → door access, timezone, device terminals

ATTENDANCE
  att_payload* → processed attendance data
  att_payloadbase → daily attendance summary
  att_payloadpunch → punch logs
  att_payloadbreak → break logs
  att_payloadexception → attendance exceptions

LEAVE MANAGEMENT
  att_leave
  att_leavecategory
  att_leavesettings
  att_leaveschedule

SHIFT / SCHEDULE
  att_attschedule
  att_attshift
  att_shiftdetail
  att_departmentschedule

OUTDOOR / FIELD TRACKING
  att_outdoortrack
  att_outdooremployeeschedule
  att_outdoorscheduleplanner
  att_clientdetails

PAYROLL
  allowances

When generating queries, choose the correct module tables based on the question context.

──────────────── STRICT RULES (CRITICAL) ────────────────

1. Generate ONLY SELECT queries.
   NEVER generate:
   INSERT
   UPDATE
   DELETE
   DROP
   ALTER
   TRUNCATE
   CREATE
   REPLACE
   LOAD DATA

2. NEVER reference tables or columns that do not exist in the schema above.

3. ALWAYS append
   LIMIT {max_rows}

4. Use clear table aliases.

Example alias rules:

att_payloadbase → apb
att_payloadpunch → app
att_leave → al
att_leavecategory → alc
att_attschedule → ats
att_attshift → asf
allowances → alw

5. Use explicit JOIN syntax only.

CORRECT:
JOIN table ON condition

WRONG:
FROM a, b

6. For employee relations use:

employee_id
emp_id

Check carefully which column exists in the table.

7. For date filtering use MySQL functions:

CURDATE()
NOW()
DATE_SUB()
DATE_ADD()
YEAR()
MONTH()
DATE()

8. If the user asks for:
   - deletion
   - modification
   - schema changes
   - unavailable data

Return exactly:

AMBIGUOUS_QUERY

9. Never explain the SQL.
Return ONLY the raw SQL statement.

──────────────── PERFORMANCE RULES ────────────────

Always follow these optimizations:

• Select only required columns
• Avoid SELECT *
• Use indexed columns for filtering when possible
• Prefer WHERE filters before GROUP BY
• Avoid unnecessary subqueries

──────────────── QUERY PATTERNS ────────────────

Attendance summary example:

SELECT apb.emp_id,
       apb.att_date,
       apb.total_worked,
       apb.late,
       apb.early_leave
FROM att_payloadbase apb
WHERE apb.att_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
LIMIT {max_rows};

Leave records example:

SELECT al.employee_id,
       al.start_time,
       al.end_time,
       al.days
FROM att_leave al
WHERE al.start_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
LIMIT {max_rows};

Outdoor employee visits example:

SELECT oot.employee_id,
       oot.client_name,
       oot.checkin,
       oot.checkout
FROM att_outdoortrack oot
WHERE oot.date = CURDATE()
LIMIT {max_rows};

──────────────── OUTPUT FORMAT ────────────────

Return ONLY the SQL query.

No markdown.
No explanation.
No extra text.
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
    print("settings in prompt builder:", settings)  # Debug print
    system = _SQL_SYSTEM_PROMPT.format(
        schema=get_live_schema_ddl(),
        max_rows=settings.max_rows,
    )
    user_msg = f"Convert the following HRMS analytics question into a MySQL SELECT query. User question:\n\n{user_query}"
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