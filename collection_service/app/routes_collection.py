from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import CollectionItem
from .mq import publish_event
from .schemas import ItemCreate, ItemOut, ItemUpdate
from .security import get_current_user_id

router = APIRouter(prefix="/api/v1/collection", tags=["collection"])


@router.get(
    "",
    response_model=list[ItemOut],
    summary="Список игр",
    description="Возвращает список игр в коллекции текущего пользователя (по JWT).",
)
def list_items(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Возвращает все элементы коллекции текущего пользователя (по user_id из JWT)."""
    return (
        db.query(CollectionItem)
        .filter(CollectionItem.user_id == user_id)
        .order_by(CollectionItem.id.desc())
        .all()
    )


@router.post(
    "",
    response_model=ItemOut,
    summary="Добавить игру",
    description="Добавляет игру в коллекцию пользователя (статус по умолчанию: planned) и публикует событие в RabbitMQ.",
)
def add_item(
    data: ItemCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Создаёт элемент коллекции и публикует событие `collection.item_added`."""
    item = CollectionItem(
        user_id=user_id,
        title=data.title,
        platform=data.platform,
        status="planned",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    publish_event(
        "collection.item_added",
        {"user_id": user_id, "item_id": item.id, "title": item.title, "platform": item.platform},
    )

    return item


@router.get(
    "/{item_id}",
    response_model=ItemOut,
    summary="Получить игру",
    description="Возвращает одну игру из коллекции по идентификатору. Доступна только владельцу (по JWT).",
)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Возвращает элемент коллекции по id (только если он принадлежит текущему пользователю)."""
    item = (
        db.query(CollectionItem)
        .filter(CollectionItem.id == item_id, CollectionItem.user_id == user_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch(
    "/{item_id}",
    response_model=ItemOut,
    summary="Обновить игру",
    description="Частично обновляет поля игры (status/rating/note) и публикует событие в RabbitMQ.",
)
def update_item(
    item_id: int,
    data: ItemUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Частично обновляет элемент коллекции и публикует событие `collection.item_updated`."""
    item = (
        db.query(CollectionItem)
        .filter(CollectionItem.id == item_id, CollectionItem.user_id == user_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Обновляем только те поля, которые реально переданы в PATCH-запросе.
    if data.status is not None:
        item.status = data.status
    if data.rating is not None:
        item.rating = data.rating
    if data.note is not None:
        item.note = data.note

    db.commit()
    db.refresh(item)

    publish_event(
        "collection.item_updated",
        {"user_id": user_id, "item_id": item.id, "status": item.status, "rating": item.rating},
    )

    return item


@router.delete(
    "/{item_id}",
    summary="Удалить игру",
    description="Удаляет игру из коллекции пользователя и публикует событие в RabbitMQ.",
)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Удаляет элемент коллекции и публикует событие `collection.item_deleted`."""
    item = (
        db.query(CollectionItem)
        .filter(CollectionItem.id == item_id, CollectionItem.user_id == user_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()

    publish_event(
        "collection.item_deleted",
        {"user_id": user_id, "item_id": item_id},
    )

    return {"deleted": True}
