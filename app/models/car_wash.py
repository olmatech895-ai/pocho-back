"""
Модели для автомоек
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class WashServiceType(str, enum.Enum):
    """Типы услуг автомойки"""
    HAND_WASH = "Ручная мойка"
    AUTOMATIC_WASH = "Автоматическая мойка"
    DRY_CLEANING = "Химчистка"
    POLISHING = "Полировка"
    WAXING = "Нанесение воска"
    VACUUM = "Пылесос"
    ENGINE_WASH = "Мойка двигателя"
    UNDERBODY_WASH = "Мойка днища"
    INTERIOR_CLEANING = "Чистка салона"
    LEATHER_TREATMENT = "Обработка кожи"
    TIRE_CLEANING = "Чистка шин"
    OTHER = "Другое"


class CarWashStatus(str, enum.Enum):
    """Статус автомойки"""
    PENDING = "pending"  # Ожидает модерации
    APPROVED = "approved"  # Одобрена
    REJECTED = "rejected"  # Отклонена
    ARCHIVED = "archived"  # Архивирована


class CarWash(Base):
    """Модель автомойки"""
    __tablename__ = "car_washes"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    name = Column(String, nullable=False, index=True)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)  # Широта
    longitude = Column(Float, nullable=False)  # Долгота
    
    # Контактная информация
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    # Режим работы
    is_24_7 = Column(Boolean, default=False, nullable=False)  # Работает 24/7
    working_hours = Column(String, nullable=True)  # Например: "08:00-22:00"
    
    # Характеристики
    description = Column(Text, nullable=True)  # Описание автомойки
    has_parking = Column(Boolean, default=False, nullable=False)  # Есть ли парковка
    has_waiting_room = Column(Boolean, default=False, nullable=False)  # Есть ли комната ожидания
    has_cafe = Column(Boolean, default=False, nullable=False)  # Есть ли кафе
    accepts_cards = Column(Boolean, default=False, nullable=False)  # Принимает ли карты
    has_vacuum = Column(Boolean, default=False, nullable=False)  # Есть ли пылесос
    has_drying = Column(Boolean, default=False, nullable=False)  # Есть ли сушка
    has_self_service = Column(Boolean, default=False, nullable=False)  # Есть ли самообслуживание
    
    # Рейтинг и статистика
    rating = Column(Float, default=0.0, nullable=False, index=True)  # Средний рейтинг
    reviews_count = Column(Integer, default=0, nullable=False)  # Количество отзывов
    
    # Статус и модерация
    status = Column(Enum(CarWashStatus), default=CarWashStatus.PENDING, nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если пользователь)
    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если админ)
    
    # Дополнительная информация
    category = Column(String, default="Автомойка", nullable=False)  # Категория
    has_promotions = Column(Boolean, default=False, nullable=False, index=True)  # Есть ли акции
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)  # Когда была одобрена
    
    # Связи
    services = relationship("CarWashService", back_populates="car_wash", cascade="all, delete-orphan")
    photos = relationship("CarWashPhoto", back_populates="car_wash", cascade="all, delete-orphan")
    reviews = relationship("CarWashReview", back_populates="car_wash", cascade="all, delete-orphan")
    
    # Индексы для геопоиска
    __table_args__ = (
        Index('idx_car_wash_location', 'latitude', 'longitude'),
    )


class CarWashService(Base):
    """Модель услуги автомойки"""
    __tablename__ = "car_wash_services"

    id = Column(Integer, primary_key=True, index=True)
    car_wash_id = Column(Integer, ForeignKey("car_washes.id"), nullable=False, index=True)
    
    service_type = Column(Enum(WashServiceType), nullable=False, index=True)
    service_name = Column(String, nullable=True)  # Название конкретной услуги (например, "Ручная мойка кузова")
    price = Column(Float, nullable=False)  # Цена в сумах
    description = Column(Text, nullable=True)  # Описание услуги
    duration_minutes = Column(Integer, nullable=True)  # Длительность услуги в минутах
    
    # Кто обновил цену
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    car_wash = relationship("CarWash", back_populates="services")
    
    # Индексы
    __table_args__ = (
        Index('idx_car_wash_service_station_type', 'car_wash_id', 'service_type'),
    )


class CarWashPhoto(Base):
    """Модель фотографии автомойки"""
    __tablename__ = "car_wash_photos"

    id = Column(Integer, primary_key=True, index=True)
    car_wash_id = Column(Integer, ForeignKey("car_washes.id"), nullable=False, index=True)
    
    photo_url = Column(String, nullable=False)  # URL фотографии
    is_main = Column(Boolean, default=False, nullable=False)  # Главная фотография
    order = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Кто загрузил
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    car_wash = relationship("CarWash", back_populates="photos")


class CarWashReview(Base):
    """Модель отзыва об автомойке"""
    __tablename__ = "car_wash_reviews"

    id = Column(Integer, primary_key=True, index=True)
    car_wash_id = Column(Integer, ForeignKey("car_washes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    rating = Column(Integer, nullable=False)  # Рейтинг от 1 до 5
    comment = Column(Text, nullable=True)  # Текст отзыва
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    car_wash = relationship("CarWash", back_populates="reviews")
    
    # Уникальность: один отзыв от пользователя на автомойку
    __table_args__ = (
        Index('idx_car_wash_review_unique', 'car_wash_id', 'user_id', unique=True),
    )











