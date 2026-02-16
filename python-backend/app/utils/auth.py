import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt

from app.config import config


def _to_bcrypt_input(password: str) -> bytes:
    """Pre-hash with SHA256 to avoid bcrypt 72-byte limit and passlib/bcrypt 4.x issues."""
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return digest.encode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = _to_bcrypt_input(plain_password)
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    pwd_bytes = _to_bcrypt_input(password)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        config.SECRET_KEY,
        algorithm=config.ALGORITHM,
    )
    return encoded_jwt
