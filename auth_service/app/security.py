import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "DUhBi61fh85J8fA47npzwo1PYXjXlsfjVXcoFRgKWcy")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(password: str) -> str:
    """Хеширует пароль bcrypt и возвращает строку-хеш.

    Важно: bcrypt имеет ограничение по длине входа — 72 байта.
    """
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password too long (max 72 bytes for bcrypt)")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет пароль против bcrypt-хеша."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject: str, user_id: int) -> str:
    """Создаёт JWT access token.

    Claim'ы:
    - sub: email пользователя
    - uid: id пользователя (users.id)
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "uid": int(user_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
