from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import hashlib
from passlib.context import CryptContext
from app.config import settings
import bcrypt

if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type('About', (object,), {'__version__': bcrypt.__version__})
    
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Перевірка пароля"""
    sha_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return pwd_context.verify(sha_hash, hashed_password)


def get_password_hash(password: str) -> str:
    """Хешування пароля"""
    sha_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(sha_hash)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Створення JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Декодування JWT токена"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None