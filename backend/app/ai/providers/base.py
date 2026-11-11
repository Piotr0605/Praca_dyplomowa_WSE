"""Wspólny interfejs dostawców porad: `generate_advice(payload) -> AdviceResult`.

Dostawcy OpenAI i Anthropic używają biblioteki standardowej (`urllib`), żeby produkcyjny obraz nie
potrzebował dodatkowych pakietów. To jedyne miejsce w aplikacji, które łączy się z internetem.
"""

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from app.ai.prompt_builder import SYSTEM_PROMPT, TEMPERATURE, user_message
from app.core.config import get_settings


@dataclass(frozen=True)
class AdviceResult:
    text: str
    model: str
    tokens_in: int | None
    tokens_out: int | None
    response_time_ms: int


class AdviceProviderError(Exception):
    """Błąd po stronie dostawcy; komunikat można pokazać użytkownikowi."""


class MissingKeyError(AdviceProviderError):
    """Brak klucza API w konfiguracji (.env)."""


class Provider(Protocol):
    def generate_advice(self, payload: dict) -> AdviceResult: ...


def _post_json(url: str, headers: dict[str, str], body: dict, provider: str) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    timeout = get_settings().AI_TIMEOUT_SECONDS
    try:
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read())
        data["_elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return data
    except urllib.error.HTTPError as error:
        raise AdviceProviderError(_http_message(provider, error)) from error
    except TimeoutError as error:
        raise AdviceProviderError(
            f"{provider}: brak odpowiedzi w ciągu {timeout} s"
        ) from error
    except urllib.error.URLError as error:
        raise AdviceProviderError(
            f"{provider}: brak połączenia ({error.reason})"
        ) from error


def _http_message(provider: str, error: urllib.error.HTTPError) -> str:
    known = {
        401: "klucz API został odrzucony",
        403: "klucz API nie ma uprawnień",
        429: "przekroczony limit zapytań u dostawcy, spróbuj za chwilę",
    }
    if error.code in known:
        return f"{provider}: {known[error.code]}"
    if 500 <= error.code < 600:
        return f"{provider}: awaria po stronie dostawcy (HTTP {error.code})"
    return f"{provider}: błąd HTTP {error.code}"


def messages_for(payload: dict) -> tuple[str, str]:
    """Prompt systemowy i wiadomość użytkownika: jedno źródło dla wszystkich dostawców."""
    return SYSTEM_PROMPT, user_message(payload)


__all__ = [
    "TEMPERATURE",
    "AdviceProviderError",
    "AdviceResult",
    "MissingKeyError",
    "Provider",
    "_post_json",
    "messages_for",
]
