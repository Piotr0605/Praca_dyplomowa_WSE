"""Reguły dotyczące kategorii."""

from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate


class CategoryNotFoundError(Exception):
    """Kategoria nie istnieje albo należy do innego użytkownika."""


class SystemCategoryError(Exception):
    """Kategorii systemowej nie można zmienić ani usunąć."""


class CategoryNameTakenError(Exception):
    """Nazwa jest już używana przez kategorię systemową lub własną."""


def to_read(category: Category) -> CategoryRead:
    return CategoryRead(
        id=category.id,
        name=category.name,
        color=category.color,
        icon=category.icon,
        is_income=category.is_income,
        is_system=category.user_id is None,
    )


def _own_category(
    repository: CategoryRepository, user_id: int, category_id: int
) -> Category:
    category = repository.get_visible(user_id, category_id)
    if category is None:
        raise CategoryNotFoundError
    if category.user_id is None:
        raise SystemCategoryError
    return category


def _commit(session: Session) -> None:
    """Zapis; jednoczesne utworzenie tej samej nazwy wychwytuje ograniczenie UNIQUE w bazie."""
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if isinstance(error.orig, UniqueViolation):
            raise CategoryNameTakenError from error
        raise


def create_category(session: Session, user_id: int, data: CategoryCreate) -> Category:
    repository = CategoryRepository(session)
    if repository.name_taken(user_id, data.name):
        raise CategoryNameTakenError
    category = repository.add(user_id, **data.model_dump())
    _commit(session)
    return category


def update_category(
    session: Session, user_id: int, category_id: int, data: CategoryUpdate
) -> Category:
    repository = CategoryRepository(session)
    category = _own_category(repository, user_id, category_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("name") is None:
        changes.pop("name", None)
    if changes.get("is_income") is None:
        changes.pop("is_income", None)
    if "name" in changes and repository.name_taken(
        user_id, changes["name"], category.id
    ):
        raise CategoryNameTakenError
    for field, value in changes.items():
        setattr(category, field, value)
    _commit(session)
    return category


def delete_category(session: Session, user_id: int, category_id: int) -> None:
    """Transakcje tracą kategorię (ON DELETE SET NULL), a reguły z nią znikają."""
    repository = CategoryRepository(session)
    repository.delete(_own_category(repository, user_id, category_id))
    session.commit()
