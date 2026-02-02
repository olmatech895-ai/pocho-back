from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_size=20,  # Размер пула соединений (увеличено для высокой нагрузки)
    max_overflow=50,  # Максимальное количество дополнительных соединений (увеличено для 20000 пользователей)
    pool_recycle=3600,  # Переиспользование соединений через час
    pool_timeout=30,  # Таймаут ожидания соединения из пула
    echo=False  # Отключить SQL логирование в продакшене
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency для получения сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




