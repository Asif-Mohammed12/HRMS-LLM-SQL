# HRMS LLM-SQL Engine

**Natural Language → SQL API** for HR analytics, powered by **Claude AI** + **FastAPI** + **PostgreSQL**.

Ask HR questions in plain English — get structured JSON data back.

---

## Architecture

```
User Question
     │
     ▼
POST /api/v1/query
     │
     ▼
Prompt Builder (versioned templates + schema)
     │
     ▼
Claude API (claude-sonnet-4-20250514)
     │
     ▼
SQL Safety Validator  ◄─── blocks INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE
     │
     ▼
Query Cache (TTL-based, in-process)
     │
     ▼
SQLAlchemy → PostgreSQL
     │
     ▼
JSON Response
```

---

## Project Structure

```
hrms_llmsql/
├── main.py                    ← Uvicorn entrypoint
├── requirements.txt
├── .env.example               ← Copy to .env and fill in values
├── pytest.ini
│
├── src/
│   ├── app.py                 ← FastAPI factory (CORS, middleware)
│   │
│   ├── core/
│   │   ├── config.py          ← Pydantic settings from .env
│   │   ├── logger.py          ← Structured JSON logging (structlog)
│   │   ├── schema.py          ← HRMS schema definition + dict for /schema
│   │   ├── prompt_builder.py  ← Versioned LLM prompt templates
│   │   ├── llm_client.py      ← Anthropic Claude API wrapper
│   │   ├── sql_validator.py   ← Multi-layer SQL safety checks
│   │   └── pipeline.py        ← End-to-end orchestration
│   │
│   ├── api/
│   │   ├── models.py          ← Pydantic request/response models
│   │   └── routes.py          ← FastAPI route handlers
│   │
│   ├── db/
│   │   └── engine.py          ← SQLAlchemy engine, safe_execute, schema discovery
│   │
│   └── utils/
│       └── cache.py           ← TTL query result cache
│
├── tests/
│   ├── test_sql_validator.py  ← Unit tests for the safety layer
│   └── test_integration.py   ← End-to-end tests (SQLite + mocked LLM)
│
└── scripts/
    └── seed_db.py             ← Creates tables + seeds sample data in PostgreSQL
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Anthropic API key

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY and PostgreSQL credentials
```

### 4. Seed the Database

```bash
python -m scripts.seed_db
```

### 5. Run the API Server

```bash
uvicorn main:app --reload --port 8000
```

Visit **http://localhost:8000/docs** for the interactive Swagger UI.

---

## API Reference

### `POST /api/v1/query`

Convert a natural-language question to SQL and execute it.

**Request:**
```json
{
  "query": "Show all employees in the Engineering department hired this year",
  "use_cache": true
}
```

**Response:**
```json
{
  "user_query": "Show all employees in the Engineering department hired this year",
  "generated_sql": "SELECT e.employee_id, e.first_name, e.last_name, e.job_title, e.hire_date FROM employees e JOIN departments d ON e.department_id = d.department_id WHERE LOWER(d.department_name) = 'engineering' AND EXTRACT(YEAR FROM e.hire_date) = EXTRACT(YEAR FROM CURRENT_DATE) AND e.employment_status = 'active' LIMIT 100",
  "data": [
    {"employee_id": 1, "first_name": "Alice", "last_name": "Smith", "job_title": "Software Engineer", "hire_date": "2024-01-15"}
  ],
  "row_count": 1,
  "cached": false,
  "prompt_version": "v2"
}
```

---

### `GET /api/v1/schema`

Returns the HRMS schema definition.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `live`    | bool | `false` | If `true`, introspects the live PostgreSQL database |

---

### `POST /api/v1/explain`

Explains a SQL query in plain English.

**Request:**
```json
{
  "query": "Show employees hired this year",
  "sql": "SELECT first_name, last_name FROM employees WHERE EXTRACT(YEAR FROM hire_date) = EXTRACT(YEAR FROM CURRENT_DATE)"
}
```

**Response:**
```json
{
  "user_query": "Show employees hired this year",
  "sql": "...",
  "explanation": "This query retrieves the first and last names of all employees who were hired during the current calendar year, by comparing the year portion of the hire_date field to today's year."
}
```

---

### `GET /api/v1/health`

Health check — reports DB connectivity and cache size.

### `DELETE /api/v1/cache`

Clears the in-process query result cache.

---

## Example Queries

```bash
# Query: employees in Engineering
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "List active employees in the Engineering department with their salaries"}'

# Query: leave requests pending
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show all pending leave requests with employee names"}'

# Query: payroll summary
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show top 10 highest paid employees this month"}'

# Query: attendance report
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Which employees worked more than 8 hours yesterday?"}'

# Get schema
curl http://localhost:8000/api/v1/schema

# Health check
curl http://localhost:8000/api/v1/health
```

---

## Running Tests

```bash
# All tests (no DB or API key required — uses SQLite + mocked LLM)
pytest

# Verbose output
pytest -v

# Specific test file
pytest tests/test_sql_validator.py -v
```

---

## Security Model

The SQL Safety Validator applies multiple layers before any query reaches the database:

| Check | Detail |
|-------|--------|
| Must start with `SELECT` | Any other statement type is immediately rejected |
| Forbidden keyword scan | `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `EXEC`, `GRANT`, `REVOKE`, `COPY` |
| Stacked statements | Detects `;` followed by additional SQL |
| Code-fence stripping | Removes ` ```sql ` wrappers the LLM might include |
| Unknown table warning | Logs warnings for table references outside the schema |
| Result limit | Prompt enforces `LIMIT 100` by default |
| Ambiguous query signal | LLM responds with `AMBIGUOUS_QUERY` for unclear/destructive requests |

---

## Improvements Over Original Code

| Area | Original | Upgraded |
|------|----------|----------|
| LLM | OpenAI GPT | Anthropic Claude |
| DB | MySQL (basic) | PostgreSQL + connection pool + `pool_pre_ping` |
| Safety | `startswith("select")` only | Multi-layer: forbidden keywords, stacked statements, comment injection, code fences |
| Config | Bare `os.getenv` | Pydantic Settings with validation |
| API | None (CLI only) | Full FastAPI with Swagger docs |
| Logging | `print()` | Structured JSON via structlog |
| Caching | None | TTL-based in-process cache |
| Schema | Hardcoded | Static definition + live auto-discovery |
| Prompts | None | Versioned system prompts with schema injection |
| Tests | None | Unit + integration tests (SQLite + mock LLM) |
| Error handling | `except Exception` → print | Typed exceptions, HTTP status codes |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | — | Your Anthropic API key |
| `CLAUDE_MODEL` | | `claude-sonnet-4-20250514` | Claude model to use |
| `POSTGRES_HOST` | ✅ | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | | `5432` | PostgreSQL port |
| `POSTGRES_USER` | ✅ | — | DB username |
| `POSTGRES_PASSWORD` | ✅ | — | DB password |
| `POSTGRES_DB` | ✅ | — | Database name |
| `MAX_ROWS` | | `100` | Default result limit |
| `QUERY_CACHE_TTL` | | `300` | Cache TTL in seconds |
| `LOG_LEVEL` | | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `ALLOWED_ORIGINS` | | `http://localhost:3000` | Comma-separated CORS origins |
