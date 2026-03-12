"""
src/api/models.py
Pydantic request / response models — OpenRouter + MySQL edition.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field, field_validator


# ── Requests ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural-language HR/CRM question",
        examples=["Show all employees hired this year in the Engineering department"],
    )
    use_cache: bool = Field(True, description="Return cached result if available")

    @field_validator("query")
    @classmethod
    def sanitise_query(cls, v: str) -> str:
        return v.strip()


class ExplainRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    sql: str = Field(..., min_length=6)


# ── Responses ─────────────────────────────────────────────────────────────────

class QueryResponse(BaseModel):
    user_query:     str
    generated_sql:  str
    data:           list[dict[str, Any]]
    row_count:      int
    cached:         bool
    prompt_version: str
    model:          str       # which OpenRouter model was used


class ExplainResponse(BaseModel):
    user_query:  str
    sql:         str
    explanation: str


class SchemaTable(BaseModel):
    name:        str
    description: str = ""
    columns:     list[dict[str, Any]]


class SchemaResponse(BaseModel):
    tables: list[SchemaTable]
    source: str = "live"      # "live" | "cached" | "static"


class HealthResponse(BaseModel):
    status:       str          # "ok" | "degraded"
    db_connected: bool
    cache_size:   int
    model:        str          # active OpenRouter model


class ErrorResponse(BaseModel):
    error:  str
    detail: str | None = None