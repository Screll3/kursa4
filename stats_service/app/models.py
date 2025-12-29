from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# ВАЖНО:
# Таблица users физически создаётся auth_service. Но чтобы SQLAlchemy смог
# корректно собрать FK (users.id) при создании event_logs, нужна "заглушка"
# users в metadata.
#
# При этом мы НЕ создаём users из этого сервиса (см. create_all(..., tables=[...]) в main.py).
users = Table(
    "users",
    Base.metadata,
    Column("id", Integer, primary_key=True),
)


class EventLog(Base):
    """Событие, полученное из RabbitMQ и сохранённое в БД (таблица event_logs)."""

    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
