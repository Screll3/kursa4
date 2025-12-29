import os
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import engine
from .logging_setup import setup_logging
from .models import CollectionItem  # noqa: F401  # импорт нужен, чтобы SQLAlchemy создал таблицу collection_items
from .routes_collection import router as collection_router

app = FastAPI(
    title="Collection Service",
    description="Коллекция видеоигр (минимальный CRUD) + JWT",
    version="0.2.0",
)

logger = setup_logging(os.getenv("SERVICE_NAME", "collection_service"))


@app.middleware("http")
async def access_log(request: Request, call_next):
    """Логирует входящие и исходящие HTTP-запросы."""
    logger.info("IN %s %s", request.method, request.url.path)
    resp = await call_next(request)
    logger.info("OUT %s %s -> %s", request.method, request.url.path, resp.status_code)
    return resp


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """Превращает ошибки валидации в ответ 400 (без 500)."""
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


@app.exception_handler(StarletteHTTPException)
async def http_handler(request: Request, exc: StarletteHTTPException):
    """Логирует штатные HTTP-ошибки (401/404/...) и возвращает их клиенту."""
    logger.info("HTTP error %s on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def any_handler(request: Request, exc: Exception):
    """Глобальный перехватчик: любые необработанные ошибки превращаем в 400 (без 500)."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=400, content={"detail": "Request processing error"})


@app.on_event("startup")
def on_startup():
    """Создаёт таблицу collection_items.

    Важно: в модели есть FK на users.id, поэтому таблица users должна уже существовать.
    Если auth_service ещё не успел создать users, делаем несколько попыток.
    """
    from .db import Base

    for attempt in range(1, 31):
        try:
            # Создаём ТОЛЬКО таблицу этого сервиса.
            # Таблица users управляется auth_service, чтобы не создать её случайно «неполной».
            Base.metadata.create_all(bind=engine, tables=[CollectionItem.__table__])
            logger.info("DB schema ensured (attempt %s)", attempt)
            break
        except Exception:
            logger.exception("DB init failed (attempt %s/30). Retrying in 2s...", attempt)
            time.sleep(2)
    else:
        # Лучше упасть при старте, чем работать без таблиц.
        raise RuntimeError("DB init failed after retries")


app.include_router(collection_router)
