"""
Схемы для станций технического обслуживания (СТО)
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ServiceTypeEnum(str, Enum):
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


class ServiceStationStatusEnum(str, Enum):
    """Статус СТО"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


# ==================== Service Price ====================

class ServicePriceBase(BaseModel):
    """Базовая схема цены на услугу"""
    service_type: ServiceTypeEnum
    service_name: Optional[str] = Field(None, max_length=255, description="Название конкретной услуги")
    price: float = Field(..., gt=0, description="Цена в сумах")
    description: Optional[str] = None


class ServicePriceCreate(ServicePriceBase):
    """Схема создания цены на услугу"""
    pass


class ServicePriceUpdate(BaseModel):
    """Схема обновления цены на услугу"""
    service_name: Optional[str] = Field(None, max_length=255)
    price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None


class ServicePriceResponse(ServicePriceBase):
    """Схема ответа с ценой на услугу"""
    id: int
    service_station_id: int
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Service Station Photo ====================

class ServiceStationPhotoBase(BaseModel):
    """Базовая схема фотографии"""
    photo_url: str
    is_main: bool = False
    order: int = 0


class ServiceStationPhotoCreate(BaseModel):
    """Схема создания фотографии"""
    is_main: bool = False
    order: int = 0


class ServiceStationPhotoResponse(ServiceStationPhotoBase):
    """Схема ответа с фотографией"""
    id: int
    service_station_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Review ====================

class ServiceStationReviewBase(BaseModel):
    """Базовая схема отзыва"""
    rating: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5")
    comment: Optional[str] = None


class ServiceStationReviewCreate(ServiceStationReviewBase):
    """Схема создания отзыва"""
    pass


class ServiceStationReviewUpdate(BaseModel):
    """Схема обновления отзыва"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ServiceStationReviewResponse(ServiceStationReviewBase):
    """Схема ответа с отзывом"""
    id: int
    service_station_id: int
    user_id: int
    user_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Service Station ====================

class ServiceStationBase(BaseModel):
    """Базовая схема СТО"""
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90, description="Широта")
    longitude: float = Field(..., ge=-180, le=180, description="Долгота")
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    is_24_7: bool = False
    working_hours: Optional[str] = None
    description: Optional[str] = None
    has_parking: bool = False
    has_waiting_room: bool = False
    has_cafe: bool = False
    accepts_cards: bool = False
    category: str = "СТО"


class ServiceStationCreate(ServiceStationBase):
    """Схема создания СТО"""
    service_prices: Optional[List[ServicePriceCreate]] = None


class ServiceStationUpdate(BaseModel):
    """Схема обновления СТО"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    is_24_7: Optional[bool] = None
    working_hours: Optional[str] = None
    description: Optional[str] = None
    has_parking: Optional[bool] = None
    has_waiting_room: Optional[bool] = None
    has_cafe: Optional[bool] = None
    accepts_cards: Optional[bool] = None
    category: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[ServiceStationStatusEnum] = None


class ServiceStationResponse(ServiceStationBase):
    """Схема ответа с СТО"""
    id: int
    rating: float
    reviews_count: int
    status: ServiceStationStatusEnum
    has_promotions: bool
    service_prices: List[ServicePriceResponse] = []
    photos: List[ServiceStationPhotoResponse] = []
    main_photo: Optional[str] = None  # URL главной фотографии
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ServiceStationDetailResponse(ServiceStationResponse):
    """Детальная схема ответа с СТО (включая отзывы)"""
    reviews: List[ServiceStationReviewResponse] = []


class ServiceStationListResponse(BaseModel):
    """Схема ответа со списком СТО"""
    service_stations: List[ServiceStationResponse]
    total: int
    skip: int
    limit: int


# ==================== Filters ====================

class ServiceStationFilter(BaseModel):
    """Схема фильтрации СТО"""
    service_type: Optional[str] = None  # Принимаем строку, конвертируем в enum при необходимости
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    max_price: Optional[float] = Field(None, gt=0)
    min_price: Optional[float] = Field(None, gt=0)
    is_24_7: Optional[bool] = None
    has_promotions: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_waiting_room: Optional[bool] = None
    has_cafe: Optional[bool] = None
    accepts_cards: Optional[bool] = None
    status: Optional[ServiceStationStatusEnum] = None
    search_query: Optional[str] = None  # Поиск по названию или адресу
    latitude: Optional[float] = None  # Для поиска по близости
    longitude: Optional[float] = None
    radius_km: Optional[float] = Field(None, gt=0)  # Радиус поиска в километрах


# ==================== Admin ====================

class ServiceStationAdminUpdate(BaseModel):
    """Схема обновления СТО админом"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    is_24_7: Optional[bool] = None
    working_hours: Optional[str] = None
    description: Optional[str] = None
    has_parking: Optional[bool] = None
    has_waiting_room: Optional[bool] = None
    has_cafe: Optional[bool] = None
    accepts_cards: Optional[bool] = None
    category: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[ServiceStationStatusEnum] = None


class BulkServicePriceUpdate(BaseModel):
    """Схема массового обновления цен на услуги"""
    service_prices: List[ServicePriceCreate] = Field(..., min_length=1)











