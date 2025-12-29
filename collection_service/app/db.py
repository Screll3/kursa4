import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# URL подключения к БД берётся из переменной окружения DATABASE_URL.
DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Базовый класс декларативных моделей SQLAlchemy."""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: отдаёт сессию SQLAlchemy и гарантирует её закрытие."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
