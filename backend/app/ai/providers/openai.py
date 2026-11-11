"""Dostawca OpenAI (Chat Completions API)."""

from app.ai.providers.base import (
    TEMPERATURE,
    AdviceResult,
    MissingKeyError,
    _post_json,
    messages_for,
)
from app.core.config import get_settings

URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider:
    def generate_advice(self, payload: dict) -> AdviceResult:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise MissingKeyError("Brak klucza OPENAI_API_KEY w pliku .env")
        system, message = messages_for(payload)
        data = _post_json(
            URL,
            {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            {
                "model": settings.OPENAI_MODEL,
                "temperature": float(TEMPERATURE),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": message},
                ],
            },
            provider="OpenAI",
        )
        usage = data.get("usage", {})
        return AdviceResult(
            text=data["choices"][0]["message"]["content"],
            model=data.get("model", settings.OPENAI_MODEL),
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            response_time_ms=data["_elapsed_ms"],
        )
