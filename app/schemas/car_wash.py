"""
Схемы для автомоек
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class WashServiceTypeEnum(str, Enum):
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


class CarWashStatusEnum(str, Enum):
    """Статус автомойки"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


# ==================== Car Wash Service ====================

class CarWashServiceBase(BaseModel):
    """Базовая схема услуги автомойки"""
    service_type: WashServiceTypeEnum
    service_name: Optional[str] = Field(None, max_length=255, description="Название конкретной услуги")
    price: float = Field(..., gt=0, description="Цена в сумах")
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, description="Длительность услуги в минутах")


class CarWashServiceCreate(CarWashServiceBase):
    """Схема создания услуги автомойки"""
    pass


class CarWashServiceUpdate(BaseModel):
    """Схема обновления услуги автомойки"""
    service_name: Optional[str] = Field(None, max_length=255)
    price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1)


class CarWashServiceResponse(CarWashServiceBase):
    """Схема ответа с услугой автомойки"""
    id: int
    car_wash_id: int
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Car Wash Photo ====================

class CarWashPhotoBase(BaseModel):
    """Базовая схема фотографии"""
    photo_url: str
    is_main: bool = False
    order: int = 0


class CarWashPhotoCreate(BaseModel):
    """Схема создания фотографии"""
    is_main: bool = False
    order: int = 0


class CarWashPhotoResponse(CarWashPhotoBase):
    """Схема ответа с фотографией"""
    id: int
    car_wash_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Review ====================

class CarWashReviewBase(BaseModel):
    """Базовая схема отзыва"""
    rating: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5")
    comment: Optional[str] = None


class CarWashReviewCreate(CarWashReviewBase):
    """Схема создания отзыва"""
    pass


class CarWashReviewUpdate(BaseModel):
    """Схема обновления отзыва"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class CarWashReviewResponse(CarWashReviewBase):
    """Схема ответа с отзывом"""
    id: int
    car_wash_id: int
    user_id: int
    user_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Car Wash ====================

class CarWashBase(BaseModel):
    """Базовая схема автомойки"""
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
    has_vacuum: bool = False
    has_drying: bool = False
    has_self_service: bool = False
    category: str = "Автомойка"


class CarWashCreate(CarWashBase):
    """Схема создания автомойки"""
    services: Optional[List[CarWashServiceCreate]] = None


class CarWashUpdate(BaseModel):
    """Схема обновления автомойки"""
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
    has_vacuum: Optional[bool] = None
    has_drying: Optional[bool] = None
    has_self_service: Optional[bool] = None
    category: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[CarWashStatusEnum] = None


class CarWashResponse(CarWashBase):
    """Схема ответа с автомойкой"""
    id: int
    rating: float
    reviews_count: int
    status: CarWashStatusEnum
    has_promotions: bool
    services: List[CarWashServiceResponse] = []
    photos: List[CarWashPhotoResponse] = []
    main_photo: Optional[str] = None  # URL главной фотографии
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CarWashDetailResponse(CarWashResponse):
    """Детальная схема ответа с автомойкой (включая отзывы)"""
    reviews: List[CarWashReviewResponse] = []


class CarWashListResponse(BaseModel):
    """Схема ответа со списком автомоек"""
    car_washes: List[CarWashResponse]
    total: int
    skip: int
    limit: int


# ==================== Filters ====================

class CarWashFilter(BaseModel):
    """Схема фильтрации автомоек"""
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
    has_vacuum: Optional[bool] = None
    has_drying: Optional[bool] = None
    has_self_service: Optional[bool] = None
    status: Optional[CarWashStatusEnum] = None
    search_query: Optional[str] = None  # Поиск по названию или адресу
    latitude: Optional[float] = None  # Для поиска по близости
    longitude: Optional[float] = None
    radius_km: Optional[float] = Field(None, gt=0)  # Радиус поиска в километрах


# ==================== Admin ====================

class CarWashAdminUpdate(BaseModel):
    """Схема обновления автомойки админом"""
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
    has_vacuum: Optional[bool] = None
    has_drying: Optional[bool] = None
    has_self_service: Optional[bool] = None
    category: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[CarWashStatusEnum] = None


class BulkCarWashServiceUpdate(BaseModel):
    """Схема массового обновления услуг автомойки"""
    services: List[CarWashServiceCreate] = Field(..., min_length=1)











