"""
src/core/llm_client.py
Thin, testable wrapper around the Anthropic Claude API.
"""
import anthropic
from src.core.config import get_settings
from src.core.logger import get_logger

log = get_logger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        settings = get_settings()
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def call_claude(system_prompt: str, user_message: str, max_tokens: int = 1024) -> str:
    """
    Send a message to Claude and return the text response.
    Raises RuntimeError on API errors.
    """
    settings = get_settings()
    client = _get_client()

    log.info("llm_request", model=settings.claude_model, user_preview=user_message[:80])

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text.strip()
        log.info("llm_response", tokens_used=response.usage.output_tokens, preview=text[:120])
        return text
    except anthropic.APIStatusError as exc:
        log.error("llm_api_error", status=exc.status_code, message=str(exc))
        raise RuntimeError(f"Claude API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        log.error("llm_connection_error", error=str(exc))
        raise RuntimeError("Could not connect to Claude API.") from exc
