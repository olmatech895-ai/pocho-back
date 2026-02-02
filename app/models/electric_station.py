"""
Модели для электрозаправок (зарядных станций)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class ConnectorType(str, enum.Enum):
    """Типы зарядных разъемов"""
    TYPE_1 = "Type 1"  # SAE J1772
    TYPE_2 = "Type 2"  # Mennekes (IEC 62196)
    CCS_TYPE_1 = "CCS Type 1"  # Combo 1
    CCS_TYPE_2 = "CCS Type 2"  # Combo 2
    CHADEMO = "CHAdeMO"
    TESLA_SUPERCHARGER = "Tesla Supercharger"
    TESLA_DESTINATION = "Tesla Destination"
    GB_T = "GB/T"  # Китайский стандарт
    OTHER = "Другое"


class ElectricStationStatus(str, enum.Enum):
    """Статус электрозаправки"""
    PENDING = "pending"  # Ожидает модерации
    APPROVED = "approved"  # Одобрена
    REJECTED = "rejected"  # Отклонена
    ARCHIVED = "archived"  # Архивирована


class ChargingPointStatus(str, enum.Enum):
    """Статус зарядной точки"""
    AVAILABLE = "available"  # Доступна
    OCCUPIED = "occupied"  # Занята
    OUT_OF_ORDER = "out_of_order"  # Неисправна
    UNKNOWN = "unknown"  # Неизвестно


class ChargingPoint(Base):
    """Модель зарядной точки"""
    __tablename__ = "charging_points"

    id = Column(Integer, primary_key=True, index=True)
    electric_station_id = Column(Integer, ForeignKey("electric_stations.id"), nullable=False, index=True)
    
    # Характеристики зарядной точки
    connector_type = Column(Enum(ConnectorType), nullable=False, index=True)  # Тип разъема
    power_kw = Column(Float, nullable=False)  # Мощность в кВт
    connector_name = Column(String, nullable=True)  # Название разъема (например, "Разъем 1")
    
    # Ценообразование
    price_per_kwh = Column(Float, nullable=True)  # Цена за кВт·ч в сумах
    price_per_minute = Column(Float, nullable=True)  # Цена за минуту в сумах
    min_price = Column(Float, nullable=True)  # Минимальная плата в сумах
    
    # Статус
    status = Column(Enum(ChargingPointStatus), default=ChargingPointStatus.UNKNOWN, nullable=False, index=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    electric_station = relationship("ElectricStation", back_populates="charging_points")
    
    # Индексы
    __table_args__ = (
        Index('idx_charging_point_station_type', 'electric_station_id', 'connector_type'),
    )


class ElectricStation(Base):
    """Модель электрозаправки"""
    __tablename__ = "electric_stations"

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
    description = Column(Text, nullable=True)  # Описание станции
    operator = Column(String, nullable=True)  # Оператор станции
    network = Column(String, nullable=True)  # Сеть зарядных станций
    
    # Дополнительные услуги
    has_parking = Column(Boolean, default=False, nullable=False)  # Есть ли парковка
    has_waiting_room = Column(Boolean, default=False, nullable=False)  # Есть ли комната ожидания
    has_cafe = Column(Boolean, default=False, nullable=False)  # Есть ли кафе
    has_restroom = Column(Boolean, default=False, nullable=False)  # Есть ли туалет
    accepts_cards = Column(Boolean, default=False, nullable=False)  # Принимает ли карты
    has_mobile_app = Column(Boolean, default=False, nullable=False)  # Есть ли мобильное приложение
    requires_membership = Column(Boolean, default=False, nullable=False)  # Требуется ли членство
    
    # Статистика зарядных точек
    total_points = Column(Integer, default=0, nullable=False)  # Общее количество точек
    available_points = Column(Integer, default=0, nullable=False)  # Доступные точки
    
    # Рейтинг и статистика
    rating = Column(Float, default=0.0, nullable=False, index=True)  # Средний рейтинг
    reviews_count = Column(Integer, default=0, nullable=False)  # Количество отзывов
    
    # Статус и модерация
    status = Column(Enum(ElectricStationStatus), default=ElectricStationStatus.PENDING, nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если пользователь)
    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если админ)
    
    # Дополнительная информация
    category = Column(String, default="Электрозаправка", nullable=False)  # Категория
    has_promotions = Column(Boolean, default=False, nullable=False, index=True)  # Есть ли акции
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)  # Когда была одобрена
    
    # Связи
    charging_points = relationship("ChargingPoint", back_populates="electric_station", cascade="all, delete-orphan")
    photos = relationship("ElectricStationPhoto", back_populates="electric_station", cascade="all, delete-orphan")
    reviews = relationship("ElectricStationReview", back_populates="electric_station", cascade="all, delete-orphan")
    
    # Индексы для геопоиска
    __table_args__ = (
        Index('idx_electric_station_location', 'latitude', 'longitude'),
    )


class ElectricStationPhoto(Base):
    """Модель фотографии электрозаправки"""
    __tablename__ = "electric_station_photos"

    id = Column(Integer, primary_key=True, index=True)
    electric_station_id = Column(Integer, ForeignKey("electric_stations.id"), nullable=False, index=True)
    
    photo_url = Column(String, nullable=False)  # URL фотографии
    is_main = Column(Boolean, default=False, nullable=False)  # Главная фотография
    order = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Кто загрузил
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    electric_station = relationship("ElectricStation", back_populates="photos")


class ElectricStationReview(Base):
    """Модель отзыва об электрозаправке"""
    __tablename__ = "electric_station_reviews"

    id = Column(Integer, primary_key=True, index=True)
    electric_station_id = Column(Integer, ForeignKey("electric_stations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    rating = Column(Integer, nullable=False)  # Рейтинг от 1 до 5
    comment = Column(Text, nullable=True)  # Текст отзыва
    
    # Дополнительные оценки
    charging_speed_rating = Column(Integer, nullable=True)  # Оценка скорости зарядки (1-5)
    price_rating = Column(Integer, nullable=True)  # Оценка цены (1-5)
    location_rating = Column(Integer, nullable=True)  # Оценка местоположения (1-5)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    electric_station = relationship("ElectricStation", back_populates="reviews")
    
    # Уникальность: один отзыв от пользователя на электрозаправку
    __table_args__ = (
        Index('idx_electric_station_review_unique', 'electric_station_id', 'user_id', unique=True),
    )










