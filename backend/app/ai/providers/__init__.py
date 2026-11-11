"""Wybór dostawcy porad według ustawienia AI_PROVIDER."""

from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.base import AdviceProviderError, AdviceResult, Provider
from app.ai.providers.mock import MockProvider
from app.ai.providers.openai import OpenAIProvider
from app.core.config import get_settings

_PROVIDERS: dict[str, type] = {
    "mock": MockProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def current_provider() -> tuple[str, Provider]:
    name = get_settings().AI_PROVIDER
    return name, _PROVIDERS[name]()


__all__ = [
    "AdviceProviderError",
    "AdviceResult",
    "Provider",
    "current_provider",
]
