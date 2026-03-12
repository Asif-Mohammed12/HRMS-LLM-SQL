"""
src/api/routes.py
FastAPI route handlers — OpenRouter + MySQL edition.
"""
from fastapi import APIRouter, HTTPException, status

from src.api.models import (
    QueryRequest, QueryResponse,
    ExplainRequest, ExplainResponse,
    SchemaResponse, SchemaTable,
    HealthResponse, ErrorResponse,
)
from src.core.pipeline import run_query_pipeline, run_explain_pipeline
from src.core.schema import SCHEMA_DICT, get_live_schema_ddl, invalidate_schema_cache
from src.core.config import get_settings
from src.db.engine import test_connection, discover_schema
from src.utils.cache import get_cache
from src.core.logger import get_logger

log = get_logger(__name__)
router = APIRouter()


# ── POST /query ───────────────────────────────────────────────────────────────
@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Natural language → MySQL → JSON results",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or ambiguous query"},
        500: {"model": ErrorResponse, "description": "Server or DB error"},
    },
)
async def query(request: QueryRequest):
    """
    Converts a plain-English HR/CRM question to a safe MySQL SELECT query
    via OpenRouter, validates it, executes it, and returns structured JSON.
    """
    try:
        result = run_query_pipeline(request.query, use_cache=request.use_cache)
        return QueryResponse(**result)
    except ValueError as exc:
        log.warning("query_validation_error", error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        log.error("query_runtime_error", error=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── GET /schema ───────────────────────────────────────────────────────────────
@router.get(
    "/schema",
    response_model=SchemaResponse,
    summary="Live MySQL schema introspection",
)
async def get_schema(live: bool = True):
    """
    Returns the schema of the connected MySQL database.
    `live=true` (default) introspects the DB directly each call.
    `live=false` returns the in-memory cached dict.
    """
    if live:
        try:
            discovered = discover_schema()
            tables = [
                SchemaTable(name=name, columns=info["columns"])
                for name, info in discovered.items()
            ]
            return SchemaResponse(tables=tables, source="live")
        except Exception as exc:
            log.error("schema_discovery_error", error=str(exc))
            raise HTTPException(status_code=500, detail=f"Schema discovery failed: {exc}")

    tables = [SchemaTable(**t) for t in SCHEMA_DICT.get("tables", [])]
    return SchemaResponse(tables=tables, source=SCHEMA_DICT.get("source", "cached"))


# ── POST /schema/refresh ──────────────────────────────────────────────────────
@router.post(
    "/schema/refresh",
    summary="Force re-discovery of schema from MySQL",
)
async def refresh_schema():
    """Clears the cached schema DDL. Useful after table migrations."""
    invalidate_schema_cache()
    new_ddl = get_live_schema_ddl()
    table_count = new_ddl.count("CREATE TABLE")
    return {"status": "refreshed", "tables_discovered": table_count}


# ── POST /explain ─────────────────────────────────────────────────────────────
@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain a SQL query in plain English",
)
async def explain(request: ExplainRequest):
    """Uses OpenRouter to explain the SQL in terms a non-technical user understands."""
    try:
        result = run_explain_pipeline(request.query, request.sql)
        return ExplainResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /health ───────────────────────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health():
    """Checks MySQL connectivity and returns cache stats."""
    db_ok = test_connection()
    cache = get_cache()
    settings = get_settings()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_connected=db_ok,
        cache_size=cache.size,
        model=settings.openrouter_model,
    )


# ── DELETE /cache ─────────────────────────────────────────────────────────────
@router.delete("/cache", summary="Clear query result cache")
async def clear_cache():
    count = get_cache().clear()
    return {"cleared_entries": count}