from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# ВАЖНО:
# В этом микросервисе таблица users физически создаётся auth_service.
# Но чтобы SQLAlchemy смог собрать FK (users.id) и создать DDL для collection_items,
# нам нужна "заглушка" таблицы users в metadata.
#
# При этом мы НЕ создаём users из этого сервиса (см. create_all(..., tables=[...]) в main.py).
users = Table(
    "users",
    Base.metadata,
    Column("id", Integer, primary_key=True),
)


class CollectionItem(Base):
    """Элемент коллекции видеоигр пользователя (таблица collection_items)."""

    __tablename__ = "collection_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False, default="PC")

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
