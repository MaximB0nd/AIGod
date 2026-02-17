from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import config
from app.database.sqlite_setup import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.api import AuthLoginIn, AuthOut, AuthRegisterIn
from app.utils.auth import create_access_token, get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthOut)
def register(data: AuthRegisterIn, db: Session = Depends(get_db)):
    """Регистрация: email, пароль, username (опционально)."""
    db_user = db.query(User).filter(User.email == data.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(data.password)
    username = data.username or data.email.split("@")[0]
    new_user = User(email=data.email, username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(
        data={"sub": new_user.email},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return AuthOut(
        id=str(new_user.id),
        email=new_user.email,
        username=new_user.username,
        token=access_token,
        refreshToken="",
    )


@router.post("/login", response_model=AuthOut)
def login(data: AuthLoginIn, db: Session = Depends(get_db)):
    """Вход по email и паролю."""
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return AuthOut(
        id=str(user.id),
        email=user.email,
        username=user.username,
        token=access_token,
        refreshToken="",
    )


@router.get("/me", response_model=AuthOut)
def me(current_user: User = Depends(get_current_user)):
    """Текущий пользователь (нужен Bearer token). Возвращает данные без пароля, token надо получить через login."""
    return AuthOut(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        token="",  # клиент должен хранить токен из login
        refreshToken="",
    )
