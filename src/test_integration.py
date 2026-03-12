"""
tests/test_integration.py
Integration tests: mock LLM + in-memory SQLite database.
"""
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine, text

# We patch the engine before importing the pipeline
SQLITE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    """Create and seed an in-memory SQLite DB, redirect engine."""
    engine = create_engine(SQLITE_URL)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE departments (
                department_id INTEGER PRIMARY KEY,
                department_name TEXT NOT NULL,
                location TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE employees (
                employee_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                hire_date TEXT,
                department_id INTEGER,
                job_title TEXT,
                salary REAL,
                employment_status TEXT DEFAULT 'active'
            )
        """))
        conn.execute(text("""
            INSERT INTO departments VALUES
                (1, 'Engineering', 'HQ'),
                (2, 'HR', 'Floor 2')
        """))
        conn.execute(text("""
            INSERT INTO employees VALUES
                (1,'Alice','Smith','a@x.com','2024-01-15',1,'Engineer',80000,'active'),
                (2,'Bob','Jones','b@x.com','2023-05-01',1,'Senior Engineer',100000,'active'),
                (3,'Carol','White','c@x.com','2022-03-10',2,'HR Manager',70000,'active')
        """))
        conn.commit()

    # Patch get_engine in db.engine to return our in-memory engine
    with patch("src.db.engine.get_engine", return_value=engine):
        yield engine


def test_safe_execute_returns_rows():
    from src.db.engine import safe_execute
    result = safe_execute("SELECT first_name FROM employees")
    assert result["row_count"] == 3
    assert result["rows"][0]["first_name"] == "Alice"


def test_safe_execute_filters():
    from src.db.engine import safe_execute
    result = safe_execute(
        "SELECT first_name FROM employees WHERE department_id = :dept",
        {"dept": 2},
    )
    assert result["row_count"] == 1
    assert result["rows"][0]["first_name"] == "Carol"


def test_pipeline_with_mocked_llm():
    """Full pipeline end-to-end with LLM mocked."""
    expected_sql = "SELECT first_name, last_name FROM employees LIMIT 100"
    with patch("src.core.pipeline.call_claude", return_value=expected_sql):
        from src.core.pipeline import run_query_pipeline
        result = run_query_pipeline("Show all employees", use_cache=False)
    assert result["row_count"] == 3
    assert "data" in result
    assert result["generated_sql"] == expected_sql


def test_pipeline_rejects_ambiguous():
    with patch("src.core.pipeline.call_claude", return_value="AMBIGUOUS_QUERY"):
        from src.core.pipeline import run_query_pipeline
        with pytest.raises(ValueError, match="ambiguous"):
            run_query_pipeline("Something unclear", use_cache=False)


def test_pipeline_rejects_destructive_sql():
    with patch("src.core.pipeline.call_claude", return_value="DELETE FROM employees"):
        from src.core.pipeline import run_query_pipeline
        with pytest.raises(ValueError):
            run_query_pipeline("Delete all employees", use_cache=False)
