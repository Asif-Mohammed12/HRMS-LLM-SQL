"""
tests/test_sql_validator.py
Unit tests for the SQL safety layer.
"""
import pytest
from src.core.sql_validator import validate_sql


# ── Valid queries ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sql", [
    "SELECT * FROM employees LIMIT 10",
    "SELECT e.first_name FROM employees e JOIN departments d ON e.department_id = d.department_id",
    "  SELECT id FROM employees  ",                     # leading whitespace
    "```sql\nSELECT 1\n```",                            # code fence stripped
])
def test_valid_select(sql):
    result = validate_sql(sql)
    assert result.upper().startswith("SELECT")


# ── Forbidden statements ──────────────────────────────────────────────────────

@pytest.mark.parametrize("sql", [
    "DELETE FROM employees WHERE 1=1",
    "DROP TABLE employees",
    "INSERT INTO employees VALUES (1,'a','b')",
    "UPDATE employees SET salary=0",
    "ALTER TABLE employees ADD COLUMN x INT",
    "TRUNCATE TABLE payroll",
    "CREATE TABLE foo (id INT)",
    "EXEC xp_cmdshell('rm -rf /')",
])
def test_forbidden_keywords(sql):
    with pytest.raises(ValueError, match="Forbidden keyword|Only SELECT"):
        validate_sql(sql)


def test_non_select():
    with pytest.raises(ValueError, match="Only SELECT"):
        validate_sql("SHOW TABLES")


def test_empty_sql():
    with pytest.raises(ValueError, match="Empty SQL"):
        validate_sql("")


def test_stacked_statements():
    with pytest.raises(ValueError, match="Multiple SQL"):
        validate_sql("SELECT 1; DROP TABLE employees")


def test_trailing_semicolon_stripped():
    sql = "SELECT 1 FROM employees;"
    result = validate_sql(sql)
    assert not result.endswith(";")


def test_code_fence_stripped():
    sql = "```sql\nSELECT id FROM employees\n```"
    result = validate_sql(sql)
    assert "```" not in result
