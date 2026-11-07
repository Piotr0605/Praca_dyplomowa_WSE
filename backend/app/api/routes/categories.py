"""Kategorie: systemowe (tylko do odczytu) i własne użytkownika."""

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser
from app.core.database import DbSession
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.category_service import (
    CategoryNameTakenError,
    CategoryNotFoundError,
    SystemCategoryError,
    create_category,
    delete_category,
    to_read,
    update_category,
)

router = APIRouter(prefix="/categories", tags=["categories"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Kategoria nie istnieje")
SYSTEM = HTTPException(
    status.HTTP_403_FORBIDDEN, "Kategorii systemowej nie można zmienić"
)
NAME_TAKEN = HTTPException(
    status.HTTP_409_CONFLICT, "Kategoria o tej nazwie już istnieje"
)


@router.get("")
def list_categories(user: CurrentUser, db: DbSession) -> list[CategoryRead]:
    return [to_read(c) for c in CategoryRepository(db).list_visible(user.id)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create(data: CategoryCreate, user: CurrentUser, db: DbSession) -> CategoryRead:
    try:
        return to_read(create_category(db, user.id, data))
    except CategoryNameTakenError as error:
        raise NAME_TAKEN from error


@router.patch("/{category_id}")
def update(
    category_id: int, data: CategoryUpdate, user: CurrentUser, db: DbSession
) -> CategoryRead:
    try:
        return to_read(update_category(db, user.id, category_id, data))
    except CategoryNotFoundError as error:
        raise NOT_FOUND from error
    except SystemCategoryError as error:
        raise SYSTEM from error
    except CategoryNameTakenError as error:
        raise NAME_TAKEN from error


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(category_id: int, user: CurrentUser, db: DbSession) -> Response:
    try:
        delete_category(db, user.id, category_id)
    except CategoryNotFoundError as error:
        raise NOT_FOUND from error
    except SystemCategoryError as error:
        raise SYSTEM from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
