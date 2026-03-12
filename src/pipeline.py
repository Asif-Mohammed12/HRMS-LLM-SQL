"""
src/core/pipeline.py
End-to-end Natural Language → SQL → Results pipeline.
"""
from src.core.prompt_builder import build_sql_prompt, build_explain_prompt, get_prompt_version
from src.core.llm_client import call_claude
from src.core.sql_validator import validate_sql
from src.db.engine import safe_execute
from src.utils.cache import get_cache
from src.core.logger import get_logger

log = get_logger(__name__)

AMBIGUOUS_SIGNAL = "AMBIGUOUS_QUERY"


def run_query_pipeline(user_query: str, use_cache: bool = True) -> dict:
    """
    Full pipeline: user_query → SQL → validated → executed → JSON.

    Returns:
        {
            "user_query": str,
            "generated_sql": str,
            "data": list[dict],
            "row_count": int,
            "cached": bool,
            "prompt_version": str,
        }
    """
    log.info("pipeline_start", user_query=user_query)

    # 1. Build prompt & call LLM
    system_prompt, user_msg = build_sql_prompt(user_query)
    raw_sql = call_claude(system_prompt, user_msg)

    # 2. Check for ambiguous / refused query signal
    if AMBIGUOUS_SIGNAL in raw_sql.upper():
        raise ValueError(
            "The query is ambiguous or cannot be answered with the available schema. "
            "Please rephrase your question with more specific details."
        )

    # 3. Validate SQL (raises ValueError on violations)
    validated_sql = validate_sql(raw_sql)

    # 4. Cache lookup
    cache = get_cache()
    if use_cache:
        cached = cache.get(user_query, validated_sql)
        if cached is not None:
            return {**cached, "cached": True}

    # 5. Execute
    result = safe_execute(validated_sql)

    # 6. Build response
    response = {
        "user_query": user_query,
        "generated_sql": validated_sql,
        "data": result["rows"],
        "row_count": result["row_count"],
        "cached": False,
        "prompt_version": get_prompt_version(),
    }

    # 7. Store in cache
    if use_cache:
        cache.set(user_query, validated_sql, response)

    log.info("pipeline_complete", row_count=result["row_count"])
    return response


def run_explain_pipeline(user_query: str, sql: str) -> dict:
    """
    Generate a plain-English explanation of a SQL query.
    """
    system_prompt, user_msg = build_explain_prompt(sql, user_query)
    explanation = call_claude(system_prompt, user_msg, max_tokens=512)
    return {
        "user_query": user_query,
        "sql": sql,
        "explanation": explanation,
    }
