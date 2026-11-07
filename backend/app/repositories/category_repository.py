"""Dostęp do tabeli categories. Każda metoda wymaga user_id."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Category


def _visible_to(user_id: int):
    """Kategorie, które użytkownik widzi: systemowe i własne."""
    return or_(Category.user_id.is_(None), Category.user_id == user_id)


class CategoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_visible(self, user_id: int) -> list[Category]:
        query = (
            select(Category)
            .where(_visible_to(user_id))
            .order_by(Category.user_id.is_not(None), func.lower(Category.name))
        )
        return list(self._session.scalars(query))

    def get_visible(self, user_id: int, category_id: int) -> Category | None:
        """Kategoria systemowa albo własna; cudza zachowuje się jak nieistniejąca."""
        return self._session.scalar(
            select(Category).where(Category.id == category_id, _visible_to(user_id))
        )

    def name_taken(
        self, user_id: int, name: str, exclude_id: int | None = None
    ) -> bool:
        query = select(Category.id).where(
            _visible_to(user_id), func.lower(Category.name) == name.lower()
        )
        if exclude_id is not None:
            query = query.where(Category.id != exclude_id)
        return self._session.scalar(query.limit(1)) is not None

    def add(self, user_id: int, **values: object) -> Category:
        category = Category(user_id=user_id, **values)
        self._session.add(category)
        self._session.flush()
        return category

    def delete(self, category: Category) -> None:
        self._session.delete(category)
        self._session.flush()
