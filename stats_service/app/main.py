import os
import threading
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import engine
from .logging_setup import setup_logging
from .models import EventLog  # noqa: F401  # импорт нужен, чтобы SQLAlchemy создал таблицу event_logs
from .mq_consumer import run_consumer_forever
from .routes_stats import router as stats_router

app = FastAPI(title="Stats Service", version="0.2.0")

logger = setup_logging(os.getenv("SERVICE_NAME", "stats_service"))


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
    """Создаёт таблицу event_logs и запускает фоновый consumer RabbitMQ."""
    from .db import Base

    # Таблица users создаётся auth_service, но event_logs ссылается на users.id.
    # Поэтому делаем несколько попыток на случай, если auth_service стартует чуть позже.
    for attempt in range(1, 31):
        try:
            Base.metadata.create_all(bind=engine, tables=[EventLog.__table__])
            logger.info("DB schema ensured (attempt %s)", attempt)
            break
        except Exception:
            logger.exception("DB init failed (attempt %s/30). Retrying in 2s...", attempt)
            time.sleep(2)
    else:
        raise RuntimeError("DB init failed after retries")

    # Consumer работает в отдельном daemon-потоке.
    t = threading.Thread(target=run_consumer_forever, daemon=True)
    t.start()


app.include_router(stats_router)
