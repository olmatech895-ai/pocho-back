from pydantic_settings import BaseSettings
from pathlib import Path
import os

# Определяем путь к .env файлу
BASE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/pocho_db"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 дней (7 * 24 * 60 минут)
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: str = "*"  # Можно указать список через запятую: "http://localhost:3000,http://localhost:8080"
    
    # SMS Service
    SMS_API_URL: str = ""
    SMS_API_TOKEN: str = ""  # Готовый токен (если предоставлен, используется напрямую)
    SMS_AUTH_EMAIL: str = ""
    SMS_AUTH_SECRET_KEY: str = ""
    SMS_FROM_NUMBER: str = "4546"
    SMS_CODE_EXPIRE_MINUTES: int = 5  # Время жизни кода в минутах
    SMS_MAIN_PHONE_NUMBER: str = ""  # Для тестирования - всегда возвращает этот код
    SMS_MAIN_CODE: str = "1234"  # Код для тестового номера
    # Обход проверки кода: для этого номера код 1111 всегда принимается (независимо от отправленного)
    SMS_BYPASS_PHONE: str = "+998900174777"
    SMS_BYPASS_CODE: str = "1111"
    
    # Security Settings
    MAX_REQUEST_SIZE: int = 1024 * 1024  # 1MB максимальный размер запроса
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60  # Запросов в минуту на IP
    RATE_LIMIT_AUTH_PER_MINUTE: int = 5  # Запросов в минуту для auth эндпоинтов
    HIDE_ERROR_DETAILS: bool = True  # Скрывать детали ошибок в продакшене
    
    # Redis для rate limiting (опционально)
    REDIS_URL: str = ""  # Если не указан, используется in-memory хранилище
    
    # File Upload Settings
    UPLOAD_DIR: str = "uploads"  # Директория для загрузки файлов
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB максимальный размер файла
    ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    BASE_URL: str = "http://localhost:8000"  # Базовый URL для генерации ссылок на файлы
    
    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else None
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Также читаем из переменных окружения системы
        extra = "ignore"


settings = Settings()

