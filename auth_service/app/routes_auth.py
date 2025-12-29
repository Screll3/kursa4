from fastapi import APIRouter, Depends, HTTPException, Header, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .schemas import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from .security import JWT_ALG, JWT_SECRET, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def decode_token(token: str) -> str:
    """Декодирует JWT и возвращает email пользователя из claim `sub`."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        sub = payload.get("sub")
        if not sub:
            raise ValueError("no sub")
        return str(sub)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.post(
    "/register",
    response_model=TokenResponse,
    summary="Регистрация",
    description="Создаёт пользователя, сохраняет пароль в виде bcrypt-хеша и возвращает JWT для последующей авторизации.",
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Регистрирует нового пользователя и возвращает access token."""
    existing = db.query(User).filter(User.email == str(data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        pw_hash = hash_password(data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = User(email=str(data.email), password_hash=pw_hash)

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(data.email), user_id=int(user.id))
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход",
    description="Проверяет email/пароль и возвращает JWT (access token) при успешной аутентификации.",
)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Проверяет учётные данные и возвращает access token."""
    user = db.query(User).filter(User.email == str(data.email)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")

    token = create_access_token(subject=str(user.email), user_id=int(user.id))
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Текущий пользователь",
    description="Возвращает email текущего пользователя по переданному JWT в заголовке Authorization: Bearer <token>.",
)
def me(authorization: str | None = Header(default=None)):
    """Возвращает информацию о текущем пользователе на основе Bearer-токена."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    email = decode_token(token)
    return MeResponse(email=email)
