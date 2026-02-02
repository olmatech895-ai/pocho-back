"""
Модели для станций технического обслуживания (СТО)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class ServiceType(str, enum.Enum):
    """Типы услуг СТО"""
    OIL_CHANGE = "Замена масла"
    ENGINE_REPAIR = "Ремонт двигателя"
    TRANSMISSION_REPAIR = "Ремонт КПП"
    BRAKE_REPAIR = "Ремонт тормозов"
    SUSPENSION_REPAIR = "Ремонт подвески"
    ELECTRICAL_REPAIR = "Ремонт электрооборудования"
    TIRE_SERVICE = "Шиномонтаж"
    WHEEL_ALIGNMENT = "Развал-схождение"
    BODY_REPAIR = "Кузовной ремонт"
    PAINTING = "Покраска"
    DIAGNOSTICS = "Диагностика"
    MAINTENANCE = "Техобслуживание"
    WASHING = "Мойка"
    OTHER = "Другое"


class ServiceStationStatus(str, enum.Enum):
    """Статус СТО"""
    PENDING = "pending"  # Ожидает модерации
    APPROVED = "approved"  # Одобрена
    REJECTED = "rejected"  # Отклонена
    ARCHIVED = "archived"  # Архивирована


class ServiceStation(Base):
    """Модель станции технического обслуживания"""
    __tablename__ = "service_stations"

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
    working_hours = Column(String, nullable=True)  # Например: "08:00-20:00"
    
    # Характеристики
    description = Column(Text, nullable=True)  # Описание СТО
    has_parking = Column(Boolean, default=False, nullable=False)  # Есть ли парковка
    has_waiting_room = Column(Boolean, default=False, nullable=False)  # Есть ли комната ожидания
    has_cafe = Column(Boolean, default=False, nullable=False)  # Есть ли кафе
    accepts_cards = Column(Boolean, default=False, nullable=False)  # Принимает ли карты
    
    # Рейтинг и статистика
    rating = Column(Float, default=0.0, nullable=False, index=True)  # Средний рейтинг
    reviews_count = Column(Integer, default=0, nullable=False)  # Количество отзывов
    
    # Статус и модерация
    status = Column(Enum(ServiceStationStatus), default=ServiceStationStatus.PENDING, nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если пользователь)
    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если админ)
    
    # Дополнительная информация
    category = Column(String, default="СТО", nullable=False)  # Категория
    has_promotions = Column(Boolean, default=False, nullable=False, index=True)  # Есть ли акции
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)  # Когда была одобрена
    
    # Связи
    service_prices = relationship("ServicePrice", back_populates="service_station", cascade="all, delete-orphan")
    photos = relationship("ServiceStationPhoto", back_populates="service_station", cascade="all, delete-orphan")
    reviews = relationship("ServiceStationReview", back_populates="service_station", cascade="all, delete-orphan")
    
    # Индексы для геопоиска
    __table_args__ = (
        Index('idx_service_station_location', 'latitude', 'longitude'),
    )


class ServicePrice(Base):
    """Модель цены на услугу"""
    __tablename__ = "service_prices"

    id = Column(Integer, primary_key=True, index=True)
    service_station_id = Column(Integer, ForeignKey("service_stations.id"), nullable=False, index=True)
    
    service_type = Column(Enum(ServiceType), nullable=False, index=True)
    service_name = Column(String, nullable=True)  # Название конкретной услуги (например, "Замена масла двигателя")
    price = Column(Float, nullable=False)  # Цена в сумах
    description = Column(Text, nullable=True)  # Описание услуги
    
    # Кто обновил цену
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    service_station = relationship("ServiceStation", back_populates="service_prices")
    
    # Уникальность: одна цена на тип услуги для одной СТО (но можно добавить несколько с разными названиями)
    __table_args__ = (
        Index('idx_service_price_station_type', 'service_station_id', 'service_type'),
    )


class ServiceStationPhoto(Base):
    """Модель фотографии СТО"""
    __tablename__ = "service_station_photos"

    id = Column(Integer, primary_key=True, index=True)
    service_station_id = Column(Integer, ForeignKey("service_stations.id"), nullable=False, index=True)
    
    photo_url = Column(String, nullable=False)  # URL фотографии
    is_main = Column(Boolean, default=False, nullable=False)  # Главная фотография
    order = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Кто загрузил
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    service_station = relationship("ServiceStation", back_populates="photos")


class ServiceStationReview(Base):
    """Модель отзыва о СТО"""
    __tablename__ = "service_station_reviews"

    id = Column(Integer, primary_key=True, index=True)
    service_station_id = Column(Integer, ForeignKey("service_stations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    rating = Column(Integer, nullable=False)  # Рейтинг от 1 до 5
    comment = Column(Text, nullable=True)  # Текст отзыва
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    service_station = relationship("ServiceStation", back_populates="reviews")
    
    # Уникальность: один отзыв от пользователя на СТО
    __table_args__ = (
        Index('idx_service_station_review_unique', 'service_station_id', 'user_id', unique=True),
    )











