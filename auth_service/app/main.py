import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import engine
from .logging_setup import setup_logging
from .models import User  # noqa: F401  # импорт нужен, чтобы SQLAlchemy создал таблицу users
from .routes_auth import router as auth_router

app = FastAPI(
    title="Auth Service",
    description="Каркас + подключение к БД через ORM",
    version="0.3.0",
)

logger = setup_logging(os.getenv("SERVICE_NAME", "auth_service"))


@app.middleware("http")
async def access_log(request: Request, call_next):
    """Логирует входящие и исходящие HTTP-запросы."""
    logger.info("IN %s %s", request.method, request.url.path)
    resp = await call_next(request)
    logger.info("OUT %s %s -> %s", request.method, request.url.path, resp.status_code)
    return resp


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """Превращает ошибки валидации FastAPI/Pydantic в ответ 400 (без 500)."""
    logger.warning(
        "Validation error on %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


@app.exception_handler(StarletteHTTPException)
async def http_handler(request: Request, exc: StarletteHTTPException):
    """Логирует штатные HTTP-ошибки (401/404/...) и возвращает их клиенту."""
    logger.info(
        "HTTP error %s on %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def any_handler(request: Request, exc: Exception):
    """Глобальный перехватчик: любые необработанные ошибки превращаем в 400 (без 500)."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=400, content={"detail": "Request processing error"})


@app.on_event("startup")
def on_startup():
    """Создаёт таблицы auth_service в БД (если их ещё нет)."""
    from .db import Base

    Base.metadata.create_all(bind=engine)


app.include_router(auth_router)
