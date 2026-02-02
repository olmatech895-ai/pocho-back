"""
Модели для системы водителей
Основано на логике Яндекс Такси
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, JSON, Enum as SQLEnum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class DriverStatus(str, enum.Enum):
    """Статус водителя"""
    PENDING = "pending"  # Ожидает проверки документов
    APPROVED = "approved"  # Одобрен, может работать
    REJECTED = "rejected"  # Отклонен администратором
    SUSPENDED = "suspended"  # Временно заблокирован
    OFFLINE = "offline"  # Не в сети (одобрен, но не работает)
    ONLINE = "online"  # В сети, готов принимать заказы


class DocumentType(str, enum.Enum):
    """Тип документа водителя"""
    PASSPORT = "passport"  # Паспорт
    DRIVING_LICENSE = "driving_license"  # Водительские права
    VEHICLE_PASSPORT = "vehicle_passport"  # Техпаспорт ТС
    INSURANCE = "insurance"  # Страховка
    PHOTO = "photo"  # Фото водителя


class DocumentStatus(str, enum.Enum):
    """Статус проверки документа"""
    PENDING = "pending"  # Ожидает проверки
    APPROVED = "approved"  # Одобрен
    REJECTED = "rejected"  # Отклонен


class VehicleType(str, enum.Enum):
    """Тип транспортного средства"""
    CAR = "car"  # Легковой автомобиль
    TRUCK = "truck"  # Грузовик
    MOTORCYCLE = "motorcycle"  # Мотоцикл
    VAN = "van"  # Фургон


class Driver(Base):
    """Модель водителя"""
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Основная информация
    phone_number = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=True, index=True)
    photo_url = Column(String, nullable=True)  # Фото водителя
    
    # Статус водителя
    status = Column(SQLEnum(DriverStatus), default=DriverStatus.PENDING, nullable=False, index=True)
    
    # Регион работы
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True, index=True)
    
    # Рейтинг и статистика
    rating = Column(Float, default=0.0, nullable=False)
    total_orders = Column(Integer, default=0, nullable=False)
    completed_orders = Column(Integer, default=0, nullable=False)
    cancelled_orders = Column(Integer, default=0, nullable=False)
    
    # Финансы
    balance = Column(Float, default=0.0, nullable=False)  # Баланс водителя
    total_earnings = Column(Float, default=0.0, nullable=False)  # Общий заработок
    
    # Геолокация
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    last_location_update = Column(DateTime(timezone=True), nullable=True)
    
    # Настройки
    is_online = Column(Boolean, default=False, nullable=False, index=True)
    auto_accept_orders = Column(Boolean, default=False, nullable=False)  # Автопринятие заказов
    
    # Комментарий администратора (при отклонении/блокировке)
    admin_comment = Column(Text, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    user = relationship("User", foreign_keys=[user_id])
    region = relationship("Region", foreign_keys=[region_id], back_populates="drivers")
    documents = relationship("DriverDocument", back_populates="driver", cascade="all, delete-orphan")
    vehicle = relationship("Vehicle", back_populates="driver", uselist=False, cascade="all, delete-orphan")
    
    # Индексы для поиска
    __table_args__ = (
        Index('idx_driver_status_online', 'status', 'is_online'),
        Index('idx_driver_location', 'current_latitude', 'current_longitude'),
    )


class DriverDocument(Base):
    """Документы водителя"""
    __tablename__ = "driver_documents"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False, index=True)
    
    # Тип документа
    document_type = Column(SQLEnum(DocumentType), nullable=False, index=True)
    
    # Файлы документа
    front_image_url = Column(String, nullable=True)  # Лицевая сторона
    back_image_url = Column(String, nullable=True)  # Обратная сторона (если есть)
    
    # Данные документа
    document_number = Column(String, nullable=True, index=True)  # Номер документа
    issue_date = Column(DateTime(timezone=True), nullable=True)  # Дата выдачи
    expiry_date = Column(DateTime(timezone=True), nullable=True)  # Дата окончания действия
    
    # Статус проверки
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False, index=True)
    
    # Комментарий администратора
    admin_comment = Column(Text, nullable=True)
    
    # Временные метки
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    driver = relationship("Driver", back_populates="documents")
    
    # Уникальность: один тип документа на водителя
    __table_args__ = (
        Index('idx_driver_document_unique', 'driver_id', 'document_type', unique=True),
    )


class Region(Base):
    """Регионы Узбекистана"""
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    name_uz = Column(String, nullable=False)  # Название на узбекском
    name_ru = Column(String, nullable=False)  # Название на русском
    name_en = Column(String, nullable=True)  # Название на английском
    
    # Географические границы региона (центр)
    center_latitude = Column(Float, nullable=True)
    center_longitude = Column(Float, nullable=True)
    
    # Активен ли регион
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Порядок отображения
    display_order = Column(Integer, default=0, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи (используем строковые ссылки для forward references)
    drivers = relationship("Driver", back_populates="region", foreign_keys="[Driver.region_id]")


class Vehicle(Base):
    """Транспортное средство водителя"""
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), unique=True, nullable=False, index=True)
    
    # Тип ТС
    vehicle_type = Column(SQLEnum(VehicleType), nullable=False, index=True)
    
    # Основная информация
    brand = Column(String, nullable=False)  # Марка (например, Chevrolet)
    model = Column(String, nullable=False)  # Модель (например, Spark)
    year = Column(Integer, nullable=True)  # Год выпуска
    color = Column(String, nullable=True)  # Цвет
    
    # Номера
    license_plate = Column(String, nullable=False, index=True)  # Гос. номер
    vehicle_passport_number = Column(String, nullable=True)  # Номер техпаспорта
    
    # Фото ТС
    photo_url = Column(String, nullable=True)
    
    # Характеристики
    capacity_kg = Column(Float, nullable=True)  # Грузоподъемность в кг
    volume_m3 = Column(Float, nullable=True)  # Объем в м³
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    driver = relationship("Driver", back_populates="vehicle")

