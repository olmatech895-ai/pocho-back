import random
import string
from datetime import datetime, timedelta, timezone
from app.core.config import settings


def generate_verification_code() -> str:
    """
    Генерация 4-значного кода верификации
    Безопасная генерация случайного кода
    """
    return "".join([str(random.randint(0, 9)) for _ in range(4)])


def generate_unique_login(prefix: str = "admin") -> str:
    """
    Генерация уникального логина
    Формат: prefix_XXXXXX (6 случайных символов)
    """
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{random_suffix}"


def generate_password(length: int = 12) -> str:
    """
    Генерация безопасного пароля
    Содержит буквы (верхний и нижний регистр), цифры и специальные символы
    Максимальная длина ограничена 72 символами (ограничение bcrypt)
    """
    # Bcrypt ограничивает пароли 72 байтами, для ASCII символов это 72 символа
    max_length = 72
    if length > max_length:
        length = max_length
    
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = "".join(random.choices(characters, k=length))
    # Гарантируем наличие хотя бы одной заглавной буквы, цифры и спецсимвола
    if not any(c.isupper() for c in password):
        password = password[0].upper() + password[1:]
    if not any(c.isdigit() for c in password):
        password = password[:-1] + str(random.randint(0, 9))
    if not any(c in "!@#$%^&*" for c in password):
        password = password[:-1] + random.choice("!@#$%^&*")
    return password


def get_code_expiration_time() -> datetime:
    """
    Получение времени истечения кода (timezone-aware)
    """
    return datetime.now(timezone.utc) + timedelta(minutes=settings.SMS_CODE_EXPIRE_MINUTES)


def is_code_expired(expires_at: datetime) -> bool:
    """
    Проверка истечения кода
    Работает с timezone-aware datetime
    """
    now = datetime.now(timezone.utc)
    # Если expires_at naive, конвертируем в UTC
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now > expires_at




