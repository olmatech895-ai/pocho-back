from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    fullname = Column(String, nullable=True)
    login = Column(String, unique=True, index=True, nullable=True)  # Уникальный логин для администратора
    hashed_password = Column(String, nullable=True)  # Хешированный пароль для администратора
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)  # Устаревшее поле - баланс теперь в users_extended.balance
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)


class BlacklistedToken(Base):
    """Модель для хранения отозванных (черный список) JWT токенов"""
    __tablename__ = "blacklisted_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)  # JWT токен
    user_id = Column(Integer, nullable=True)  # ID пользователя (опционально)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Время добавления в черный список
