"""
Расширенные модели пользователя для PoCho приложения
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class UserExtended(Base):
    """Расширенная модель пользователя"""
    __tablename__ = "users_extended"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Основная информация
    phone = Column(String, unique=True, index=True, nullable=False)  # Дублируем для быстрого доступа
    name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    avatar = Column(String, nullable=True)  # URL аватара
    
    # Настройки
    language = Column(String, default="ru", nullable=False)
    
    # Финансы
    balance = Column(Float, default=0.0, nullable=False)
    
    # Статус и рейтинг
    level = Column(String, default="Новичок", nullable=False)  # Новичок, Серебряный, Золотой, Платиновый
    rating = Column(Float, default=0.0, nullable=False)
    
    # Статистика (кэшируем для производительности)
    total_stations_visited = Column(Integer, default=0, nullable=False)
    total_spent = Column(Float, default=0.0, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("UserNotification", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    """Профиль пользователя с документами и настройками"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_extended.id"), unique=True, nullable=False, index=True)
    
    # Документы (JSON для гибкости)
    passport_image_url = Column(String, nullable=True)
    passport_verified = Column(Boolean, default=False, nullable=False)
    passport_uploaded_at = Column(DateTime(timezone=True), nullable=True)
    
    driving_license_image_url = Column(String, nullable=True)
    driving_license_verified = Column(Boolean, default=False, nullable=False)
    driving_license_uploaded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Настройки (JSON для расширяемости)
    settings = Column(JSON, default=dict, nullable=False)  # {"notifications_enabled": true, "language": "ru"}
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("UserExtended", back_populates="profile")


class UserFavorite(Base):
    """Избранное пользователя (универсальная таблица для всех типов)"""
    __tablename__ = "user_favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_extended.id"), nullable=False, index=True)
    
    # Тип избранного
    favorite_type = Column(String, nullable=False, index=True)  # fuel_station, restaurant, car_service, car_wash, charging_station
    
    # ID объекта из внешней системы (не храним полные данные здесь)
    place_id = Column(Integer, nullable=False, index=True)
    
    # Метаданные (JSON для гибкости)
    extra_data = Column(JSON, nullable=True)  # Дополнительные данные если нужны
    
    # Временные метки
    added_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Уникальность: один пользователь не может добавить одно место дважды одного типа
    __table_args__ = (
        UniqueConstraint('user_id', 'favorite_type', 'place_id', name='uq_user_favorite'),
    )
    
    # Связи
    user = relationship("UserExtended", back_populates="favorites")


class UserAchievement(Base):
    """
    Достижения пользователя
    Отдельная таблица для каждого пользователя с типом достижения и статусом
    """
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_extended.id"), nullable=False, index=True)
    
    # Тип достижения (например: "first_refuel", "star_driver", "lover", "premium")
    achievement_type = Column(String, nullable=False, index=True)
    
    # Статус разблокировки (true - разблокировано, false - заблокировано)
    unlocked = Column(Boolean, default=False, nullable=False, index=True)
    unlocked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Метаданные достижения для отображения
    icon = Column(String, nullable=True)  # Иконка достижения
    title = Column(String, nullable=True)  # Название достижения
    description = Column(Text, nullable=True)  # Описание достижения
    color = Column(Integer, nullable=True)  # Цвет в формате int (для UI)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Уникальность: одно достижение каждого типа на пользователя
    __table_args__ = (
        UniqueConstraint('user_id', 'achievement_type', name='uq_user_achievement_type'),
    )
    
    # Связи
    user = relationship("UserExtended", back_populates="achievements")


class UserNotification(Base):
    """Настройки уведомлений пользователя"""
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_extended.id"), unique=True, nullable=False, index=True)
    
    # Настройки уведомлений
    enabled = Column(Boolean, default=True, nullable=False)
    price_alerts = Column(Boolean, default=True, nullable=False)
    new_stations = Column(Boolean, default=True, nullable=False)
    promotions = Column(Boolean, default=True, nullable=False)
    reviews = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("UserExtended", back_populates="notifications")


class Transaction(Base):
    """Транзакции пользователя"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_extended.id"), nullable=False, index=True)
    
    # Тип транзакции
    type = Column(String, nullable=False, index=True)  # top_up, purchase, refund, bonus, etc.
    
    # Сумма (положительная для пополнения, отрицательная для расходов)
    amount = Column(Float, nullable=False)
    
    # Описание
    description = Column(Text, nullable=True)
    
    # Метаданные (JSON для дополнительной информации)
    extra_data = Column(JSON, nullable=True)  # {"place_id": 1, "fuel_type": "AI-95", etc.}
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Связи
    user = relationship("UserExtended", back_populates="transactions")


class UserStatistics(Base):
    """Статистика пользователя (кэшированная для производительности)"""
    __tablename__ = "user_statistics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_extended.id"), unique=True, nullable=False, index=True)
    
    # Счетчики избранного
    favorite_fuel_stations_count = Column(Integer, default=0, nullable=False)
    favorite_restaurants_count = Column(Integer, default=0, nullable=False)
    favorite_car_services_count = Column(Integer, default=0, nullable=False)
    favorite_car_washes_count = Column(Integer, default=0, nullable=False)
    favorite_charging_stations_count = Column(Integer, default=0, nullable=False)
    total_favorites_count = Column(Integer, default=0, nullable=False)
    
    # Общая статистика
    total_spent = Column(Float, default=0.0, nullable=False)
    average_rating_given = Column(Float, default=0.0, nullable=False)
    reviews_written = Column(Integer, default=0, nullable=False)
    
    # Временные метки
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи (опционально, если нужен relationship)
    # user = relationship("UserExtended", backref="statistics")

