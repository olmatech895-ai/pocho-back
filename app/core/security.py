from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля
    Пароли генерируются длиной 12 символов (безопасно для bcrypt, лимит 72 байта)
    """
    # Bcrypt принимает bytes
    password_bytes = plain_password.encode('utf-8')
    # Обрезаем до 72 байт если нужно (пароли 12 символов, но на всякий случай)
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля
    Пароли генерируются длиной 12 символов (безопасно для bcrypt, лимит 72 байта)
    """
    # Bcrypt принимает bytes
    password_bytes = password.encode('utf-8')
    # Обрезаем до 72 байт если нужно (пароли 12 символов, но на всякий случай)
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    # Генерируем salt и хешируем
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена
    python-jose требует, чтобы 'sub' был строкой, поэтому если передан словарь,
    извлекаем phone_number для sub и сохраняем остальные данные в других полях
    """
    to_encode = data.copy()
    
    # Если sub - словарь, преобразуем в строку (phone_number) и сохраняем id отдельно
    if "sub" in to_encode and isinstance(to_encode["sub"], dict):
        sub_dict = to_encode["sub"]
        phone_number = sub_dict.get("phone_number")
        user_id = sub_dict.get("id")
        
        if phone_number:
            to_encode["sub"] = phone_number  # python-jose требует строку
            if user_id:
                to_encode["user_id"] = user_id  # Сохраняем id в отдельном поле
        else:
            raise ValueError("phone_number is required in sub dict")
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # JWT требует timestamp (секунды с эпохи)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt




