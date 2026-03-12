# LLM‑SQL Project for HRMS Application

## Goal Description
Create a Python‑based project that integrates a Large Language Model (LLM) to generate SQL queries from natural‑language HR‑related requests (e.g., *"list all employees hired in the last month"*). The project will expose a simple library (`hrms_llmsql`) that:
- Accepts a user prompt.
- Uses an LLM (OpenAI/Claude/etc.) to translate the prompt into a parameterised SQL statement.
- Executes the statement against a configurable HRMS database (via SQLAlchemy).
- Returns the query results in a Python data structure.

## Proposed Changes
---
### Project Structure
#### [NEW] hrms_llmsql/
- `src/`
  - `__init__.py`
  - `config.py` – configuration handling (LLM API keys, DB connection string).
  - `llm_client.py` – thin wrapper around the chosen LLM provider.
  - `sql_generator.py` – prompt templates, response parsing, safe SQL generation.
  - `db.py` – SQLAlchemy engine/session helper.
  - `main.py` – example CLI script demonstrating end‑to‑end usage.
- `tests/`
  - `test_sql_generator.py` – unit tests for prompt → SQL conversion.
  - `test_integration.py` – spin‑up an SQLite in‑memory DB, run a generated query, verify results.
- `requirements.txt` – list of dependencies (openai, sqlalchemy, pytest, python‑dotenv).
- `README.md` – project overview, setup, and usage instructions.
---
### Core Files
#### [NEW] src/config.py
```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
DB_URL = os.getenv("HRMS_DB_URL", "sqlite:///hrms.db")
```
#### [NEW] src/llm_client.py
```python
import os
from openai import OpenAI
from .config import LLM_API_KEY, LLM_MODEL

client = OpenAI(api_key=LLM_API_KEY)

def generate_sql(prompt: str) -> str:
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()
```
#### [NEW] src/sql_generator.py
```python
from .llm_client import generate_sql
from .db import safe_execute

def query_hrms(prompt: str):
    sql = generate_sql(prompt)
    return safe_execute(sql)
```
#### [NEW] src/db.py
```python
from sqlalchemy import create_engine, text
from .config import DB_URL

engine = create_engine(DB_URL)

def safe_execute(sql: str):
    # Very basic safety – allow only SELECT statements for this demo
    if not sql.lstrip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return [dict(row) for row in result]
```
#### [NEW] src/main.py
```python
import argparse
from .sql_generator import query_hrms

def main():
    parser = argparse.ArgumentParser(description="HRMS LLM‑SQL demo")
    parser.add_argument("prompt", help="Natural‑language request, e.g. 'list employees hired last month'")
    args = parser.parse_args()
    try:
        rows = query_hrms(args.prompt)
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```
---
## Verification Plan
### Automated Tests
1. **Unit test – `test_sql_generator.py`**
   - Mock `llm_client.generate_sql` to return a known SELECT statement.
   - Call `sql_generator.query_hrms` and assert that the returned rows match the mocked DB response.
   - Run with `pytest tests/test_sql_generator.py`.
2. **Integration test – `test_integration.py`**
   - Create an in‑memory SQLite DB, populate a simple `employees` table.
   - Patch `config.DB_URL` to point to the in‑memory DB.
   - Use the real `llm_client` but with a deterministic prompt that the LLM model is known to translate (or mock the LLM call to a fixed SELECT).
   - Execute `sql_generator.query_hrms` and verify the correct rows are returned.
   - Run with `pytest tests/test_integration.py`.
### Manual Verification
1. Install dependencies: `pip install -r requirements.txt`.
2. Populate a local SQLite file `hrms.db` with a sample `employees` table.
3. Run the demo script:
   ```bash
   python -m hrms_llmsql.src.main "list all employees hired in the last 7 days"
   ```
4. Verify the printed JSON‑like rows match the expected data.
5. Attempt a non‑SELECT prompt (e.g., "delete all records") and confirm the tool raises a clear error.
---
## Additional Notes
- The project will be created under the workspace `c:\Projects\Ai agent\HRMS-LLMSQL` as requested.
- Environment variables for the LLM API key and DB URL are loaded from a `.env` file for convenience.
- Future extensions could add INSERT/UPDATE support with parameter sanitisation.
