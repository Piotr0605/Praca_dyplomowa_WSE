"""Dostawca Anthropic (Messages API)."""

from app.ai.providers.base import (
    TEMPERATURE,
    AdviceResult,
    MissingKeyError,
    _post_json,
    messages_for,
)
from app.core.config import get_settings

URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MAX_TOKENS = 2000


class AnthropicProvider:
    def generate_advice(self, payload: dict) -> AdviceResult:
        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            raise MissingKeyError("Brak klucza ANTHROPIC_API_KEY w pliku .env")
        system, message = messages_for(payload)
        data = _post_json(
            URL,
            {
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": API_VERSION,
            },
            {
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": MAX_TOKENS,
                "temperature": float(TEMPERATURE),
                "system": system,
                "messages": [{"role": "user", "content": message}],
            },
            provider="Anthropic",
        )
        usage = data.get("usage", {})
        return AdviceResult(
            text="".join(
                block["text"] for block in data["content"] if block["type"] == "text"
            ),
            model=data.get("model", settings.ANTHROPIC_MODEL),
            tokens_in=usage.get("input_tokens"),
            tokens_out=usage.get("output_tokens"),
            response_time_ms=data["_elapsed_ms"],
        )
