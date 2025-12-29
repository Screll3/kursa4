import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

JWT_SECRET = os.getenv("JWT_SECRET", "DUhBi61fh85J8fA47npzwo1PYXjXlsfjVXcoFRgKWcy")
JWT_ALG = os.getenv("JWT_ALG", "HS256")

bearer = HTTPBearer(auto_error=False)


def _decode_token(creds: HTTPAuthorizationCredentials | None) -> dict:
    """Достаёт и декодирует JWT из заголовка Authorization (Bearer)."""
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = creds.credentials
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int:
    """Возвращает user_id (users.id) из JWT (claim: uid)."""
    payload = _decode_token(creds)
    uid = payload.get("uid")
    if uid is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        return int(uid)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_email(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    """Возвращает email из JWT (claim: sub). Используется для совместимости/отладки."""
    payload = _decode_token(creds)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    return str(sub)
