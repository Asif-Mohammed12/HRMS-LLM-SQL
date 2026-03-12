"""
src/api/models.py
Pydantic models for FastAPI request / response validation.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field, field_validator


# ── Requests ────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="Natural-language HR question")
    use_cache: bool = Field(True, description="Return cached result if available")

    @field_validator("query")
    @classmethod
    def sanitise_query(cls, v: str) -> str:
        return v.strip()


class ExplainRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="Original natural-language question")
    sql: str = Field(..., min_length=6, description="SQL query to explain")


# ── Responses ───────────────────────────────────────────────────────────────

class QueryResponse(BaseModel):
    user_query: str
    generated_sql: str
    data: list[dict[str, Any]]
    row_count: int
    cached: bool
    prompt_version: str


class ExplainResponse(BaseModel):
    user_query: str
    sql: str
    explanation: str


class SchemaColumn(BaseModel):
    name: str
    type: str
    pk: bool = False
    fk: str | None = None
    nullable: bool = True


class SchemaTable(BaseModel):
    name: str
    description: str = ""
    columns: list[dict[str, Any]]


class SchemaResponse(BaseModel):
    tables: list[SchemaTable]
    source: str = "static"  # "static" | "live"


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    cache_size: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
