"""Dane wejściowe i odpowiedzi API dotyczące kategorii."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Color = Annotated[
    str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$"), AfterValidator(str.upper)
]
Icon = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]


class CategoryCreate(BaseModel):
    name: CategoryName
    color: Color | None = None
    icon: Icon | None = None
    is_income: bool = False


class CategoryUpdate(BaseModel):
    """Wszystkie pola opcjonalne: zmieniane są tylko te, które przysłano."""

    name: CategoryName | None = None
    color: Color | None = None
    icon: Icon | None = None
    is_income: bool | None = None


class CategoryRead(BaseModel):
    id: int
    name: str
    color: str | None
    icon: str | None
    is_income: bool
    is_system: bool = Field(
        description="Kategoria wspólna dla wszystkich; tylko do odczytu"
    )
