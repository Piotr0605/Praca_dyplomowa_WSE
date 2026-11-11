"""Dane wejściowe i odpowiedzi API porad."""

import datetime as dt
from typing import Any

from pydantic import BaseModel, model_validator


class AdviceRequest(BaseModel):
    date_from: dt.date
    date_to: dt.date

    @model_validator(mode="after")
    def check_order(self) -> "AdviceRequest":
        if self.date_from > self.date_to:
            raise ValueError("date_from jest po date_to")
        return self


class AdviceRead(BaseModel):
    id: int
    period_start: dt.date
    period_end: dt.date
    provider: str
    model: str
    response_text: str
    tokens_in: int | None
    tokens_out: int | None
    prompt_version: str
    response_time_ms: int | None
    created_at: dt.datetime
    # Kopia pakietu wysłanego do modelu: użytkownik może sprawdzić, co opuściło komputer.
    prompt_payload: dict[str, Any]

    model_config = {"from_attributes": True}


class AdviceResponse(BaseModel):
    advice: AdviceRead
    # Porada z cache: dane okresu się nie zmieniły, więc model nie był pytany ponownie.
    cached: bool
