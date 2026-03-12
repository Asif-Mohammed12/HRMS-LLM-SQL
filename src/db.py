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
