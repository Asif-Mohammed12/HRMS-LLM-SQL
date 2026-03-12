"""
src/app.py
FastAPI application factory with middleware, CORS, and exception handlers.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.core.logger import setup_logging, get_logger
from src.api.routes import router

setup_logging()
log = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="HRMS LLM-SQL Engine",
        description=(
            "Natural Language → SQL API for HRMS analytics powered by Claude AI. "
            "Ask HR questions in plain English and get structured data back."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5500",  # VS Code Live Server (for hrms-chart.html)
        "null",                   # file:// origin (opening HTML directly in browser)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.error("unhandled_exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "HRMS LLM-SQL Engine", "docs": "/docs"}

    log.info("app_created", env=settings.app_env)
    return app


app = create_app()