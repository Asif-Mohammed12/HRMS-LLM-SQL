"""
src/core/pipeline.py
End-to-end Natural Language → SQL → Results pipeline.
"""
from src.core.prompt_builder import build_sql_prompt, build_explain_prompt, get_prompt_version
from src.core.llm_client import call_llm
from src.core.sql_validator import validate_sql
from src.db.engine import safe_execute
from src.utils.cache import get_cache
from src.core.logger import get_logger

log = get_logger(__name__)

AMBIGUOUS_SIGNAL = "AMBIGUOUS_QUERY"


def run_query_pipeline(user_query: str, use_cache: bool = True) -> dict:
    """
    Full pipeline: user_query → prompt → OpenRouter LLM → validate SQL → execute → JSON.

    Returns:
        {
            "user_query"    : str,
            "generated_sql" : str,
            "data"          : list[dict],
            "row_count"     : int,
            "cached"        : bool,
            "prompt_version": str,
            "model"         : str,
        }
    """
    from src.core.config import get_settings
    log.info("pipeline_start", user_query=user_query)
    # print("Pipeline input query:", user_query)  # Debug print
    # 1. Build prompt
    system_prompt, user_msg = build_sql_prompt(user_query)

    # 2. Call OpenRouter
    raw_sql = call_llm(system_prompt, user_msg)

    # 3. Detect ambiguous / refused signal
    if AMBIGUOUS_SIGNAL in raw_sql.upper():
        raise ValueError(
            "The query is ambiguous or cannot be answered with the available schema. "
            "Please rephrase your question with more specific details."
        )

    # 4. Validate SQL safety
    validated_sql = validate_sql(raw_sql)

    # 5. Cache lookup
    cache = get_cache()
    if use_cache:
        cached = cache.get(user_query, validated_sql)
        if cached is not None:
            return {**cached, "cached": True}

    # 6. Execute against MySQL
    result = safe_execute(validated_sql)

    # 7. Build response
    settings = get_settings()
    response = {
        "user_query":     user_query,
        "generated_sql":  validated_sql,
        "data":           result["rows"],
        "row_count":      result["row_count"],
        "cached":         False,
        "prompt_version": get_prompt_version(),
        "model":          settings.openrouter_model,
    }

    # 8. Cache result
    if use_cache:
        cache.set(user_query, validated_sql, response)

    log.info("pipeline_complete", row_count=result["row_count"])
    return response


def run_explain_pipeline(user_query: str, sql: str) -> dict:
    """Plain-English explanation of a SQL query."""
    system_prompt, user_msg = build_explain_prompt(sql, user_query)
    explanation = call_llm(system_prompt, user_msg, max_tokens=512)
    return {
        "user_query":  user_query,
        "sql":         sql,
        "explanation": explanation,
    }