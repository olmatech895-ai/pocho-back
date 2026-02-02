"""
Модели для заправочных станций
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class FuelType(str, enum.Enum):
    """Типы топлива"""
    AI_80 = "AI-80"
    AI_91 = "AI-91"
    AI_95 = "AI-95"
    AI_98 = "AI-98"
    DIESEL = "Дизель"
    GAS = "Газ"


class StationStatus(str, enum.Enum):
    """Статус станции"""
    PENDING = "pending"  # Ожидает модерации (для пользовательских добавлений)
    APPROVED = "approved"  # Одобрена
    REJECTED = "rejected"  # Отклонена
    ARCHIVED = "archived"  # Архивирована


class GasStation(Base):
    """Модель заправочной станции"""
    __tablename__ = "gas_stations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    name = Column(String, nullable=False, index=True)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)  # Широта
    longitude = Column(Float, nullable=False)  # Долгота
    
    # Контактная информация
    phone = Column(String, nullable=True)
    
    # Режим работы
    is_24_7 = Column(Boolean, default=False, nullable=False)  # Работает 24/7
    working_hours = Column(String, nullable=True)  # Например: "08:00-22:00"
    
    # Рейтинг и статистика
    rating = Column(Float, default=0.0, nullable=False, index=True)  # Средний рейтинг
    reviews_count = Column(Integer, default=0, nullable=False)  # Количество отзывов
    
    # Статус и модерация
    status = Column(Enum(StationStatus), default=StationStatus.PENDING, nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если пользователь)
    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если админ)
    
    # Дополнительная информация
    category = Column(String, default="Заправка", nullable=False)  # Категория
    has_promotions = Column(Boolean, default=False, nullable=False, index=True)  # Есть ли акции
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)  # Когда была одобрена
    
    # Связи
    fuel_prices = relationship("FuelPrice", back_populates="gas_station", cascade="all, delete-orphan")
    photos = relationship("GasStationPhoto", back_populates="gas_station", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="gas_station", cascade="all, delete-orphan")
    
    # Индексы для геопоиска
    __table_args__ = (
        Index('idx_gas_station_location', 'latitude', 'longitude'),
    )


class FuelPrice(Base):
    """Модель цены на топливо"""
    __tablename__ = "fuel_prices"

    id = Column(Integer, primary_key=True, index=True)
    gas_station_id = Column(Integer, ForeignKey("gas_stations.id"), nullable=False, index=True)
    
    fuel_type = Column(Enum(FuelType), nullable=False, index=True)
    price = Column(Float, nullable=False)  # Цена в сумах
    
    # Кто обновил цену
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    gas_station = relationship("GasStation", back_populates="fuel_prices")
    
    # Уникальность: одна цена на тип топлива для одной станции
    __table_args__ = (
        Index('idx_fuel_price_unique', 'gas_station_id', 'fuel_type', unique=True),
    )


class GasStationPhoto(Base):
    """Модель фотографии заправочной станции"""
    __tablename__ = "gas_station_photos"

    id = Column(Integer, primary_key=True, index=True)
    gas_station_id = Column(Integer, ForeignKey("gas_stations.id"), nullable=False, index=True)
    
    photo_url = Column(String, nullable=False)  # URL фотографии
    is_main = Column(Boolean, default=False, nullable=False)  # Главная фотография
    order = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Кто загрузил
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    gas_station = relationship("GasStation", back_populates="photos")


class Review(Base):
    """Модель отзыва о заправочной станции"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    gas_station_id = Column(Integer, ForeignKey("gas_stations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    rating = Column(Integer, nullable=False)  # Рейтинг от 1 до 5
    comment = Column(Text, nullable=True)  # Текст отзыва
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    gas_station = relationship("GasStation", back_populates="reviews")
    
    # Уникальность: один отзыв от пользователя на станцию
    __table_args__ = (
        Index('idx_review_unique', 'gas_station_id', 'user_id', unique=True),
    )











