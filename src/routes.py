"""
src/api/routes.py
All FastAPI route handlers.
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import OperationalError

from src.api.models import (
    QueryRequest, QueryResponse,
    ExplainRequest, ExplainResponse,
    SchemaResponse, SchemaTable,
    HealthResponse, ErrorResponse,
)
from src.core.pipeline import run_query_pipeline, run_explain_pipeline
from src.core.schema import SCHEMA_DICT
from src.db.engine import get_engine, discover_schema
from src.utils.cache import get_cache
from src.core.logger import get_logger

log = get_logger(__name__)

router = APIRouter()


# ── POST /query ──────────────────────────────────────────────────────────────
@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Convert natural language to SQL and execute",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or ambiguous query"},
        500: {"model": ErrorResponse, "description": "Server or database error"},
    },
)
async def query(request: QueryRequest):
    """
    Accept a natural-language HR question, generate safe SQL via Claude,
    validate, execute against PostgreSQL, and return structured results.
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


# ── GET /schema ──────────────────────────────────────────────────────────────
@router.get(
    "/schema",
    response_model=SchemaResponse,
    summary="Return HRMS database schema",
)
async def get_schema(live: bool = False):
    """
    Returns the HRMS schema.
    - `live=false` (default): returns the static schema definition.
    - `live=true`: introspects the connected PostgreSQL database.
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

    tables = [SchemaTable(**t) for t in SCHEMA_DICT["tables"]]
    return SchemaResponse(tables=tables, source="static")


# ── POST /explain ────────────────────────────────────────────────────────────
@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain a SQL query in plain English",
)
async def explain(request: ExplainRequest):
    """
    Given an original question and a SQL query, return a plain-English
    explanation suitable for non-technical stakeholders.
    """
    try:
        result = run_explain_pipeline(request.query, request.sql)
        return ExplainResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /health ───────────────────────────────────────────────────────────────
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
)
async def health():
    db_ok = False
    try:
        engine = get_engine()
        with engine.connect():
            db_ok = True
    except OperationalError:
        pass

    cache = get_cache()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_connected=db_ok,
        cache_size=cache.size,
    )


# ── DELETE /cache ─────────────────────────────────────────────────────────────
@router.delete(
    "/cache",
    summary="Clear the query result cache",
)
async def clear_cache():
    cache = get_cache()
    count = cache.clear()
    return {"cleared_entries": count}
