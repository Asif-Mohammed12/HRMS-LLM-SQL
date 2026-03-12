from .llm_client import generate_sql
from .db import safe_execute

def query_hrms(prompt: str):
    sql = generate_sql(prompt)
    return safe_execute(sql)
