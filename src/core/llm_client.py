"""
src/core/llm_client.py
OpenRouter LLM client using the OpenAI-compatible SDK.

OpenRouter sits in front of 100+ models (GPT-4o, Claude, Llama, Mistral, etc.)
and exposes them all through a single OpenAI-compatible endpoint.
We use the official `openai` Python SDK pointed at https://openrouter.ai/api/v1.

Key headers required by OpenRouter:
  HTTP-Referer  — your site URL  (for their analytics / ToS)
  X-Title       — your app name  (shown in their dashboard)
"""
from openai import OpenAI, APIStatusError, APIConnectionError
from src.core.config import get_settings
from src.core.logger import get_logger

log = get_logger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        s = get_settings()
        _client = OpenAI(
            api_key=s.openrouter_api_key,
            base_url=s.openrouter_base_url,
            default_headers={
                "HTTP-Referer": s.openrouter_site_url,
                "X-Title": s.openrouter_site_name,
            },
        )
        log.info("openrouter_client_created", model=s.openrouter_model)
    return _client


def call_llm(system_prompt: str, user_message: str, max_tokens: int = 1024) -> str:
    """
    Send a chat message to OpenRouter and return the text response.

    The function uses system + user message format which works across
    all OpenRouter-hosted models (GPT, Claude, Llama, Mistral, etc.).

    Raises RuntimeError on API or connection errors.
    """
    s = get_settings()
    client = _get_client()

    log.info(
        "llm_request",
        model=s.openrouter_model,
        user_preview=user_message[:80],
    )

    try:
        response = client.chat.completions.create(
            model=s.openrouter_model,
            max_tokens=max_tokens,
            temperature=0,          # deterministic SQL — never use high temp here
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
        )
        text = response.choices[0].message.content.strip()
        usage = response.usage

        log.info(
            "llm_response",
            prompt_tokens=usage.prompt_tokens if usage else "?",
            completion_tokens=usage.completion_tokens if usage else "?",
            preview=text[:120],
        )
        return text

    except APIStatusError as exc:
        log.error("openrouter_api_error", status=exc.status_code, message=str(exc))
        raise RuntimeError(
            f"OpenRouter API error {exc.status_code}: {exc.message}"
        ) from exc

    except APIConnectionError as exc:
        log.error("openrouter_connection_error", error=str(exc))
        raise RuntimeError("Could not connect to OpenRouter API.") from exc


# ── Backwards-compat alias (pipeline.py calls call_claude) ────────────────────
call_claude = call_llm