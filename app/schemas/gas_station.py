"""
Схемы для заправочных станций
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class FuelTypeEnum(str, Enum):
    """Типы топлива"""
    AI_80 = "AI-80"
    AI_91 = "AI-91"
    AI_95 = "AI-95"
    AI_98 = "AI-98"
    DIESEL = "Дизель"
    GAS = "Газ"


class StationStatusEnum(str, Enum):
    """Статус станции"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


# ==================== Fuel Price ====================

class FuelPriceBase(BaseModel):
    """Базовая схема цены на топливо"""
    fuel_type: FuelTypeEnum
    price: float = Field(..., gt=0, description="Цена в сумах")


class FuelPriceCreate(FuelPriceBase):
    """Схема создания цены на топливо"""
    pass


class FuelPriceUpdate(BaseModel):
    """Схема обновления цены на топливо"""
    price: float = Field(..., gt=0, description="Цена в сумах")


class FuelPriceResponse(FuelPriceBase):
    """Схема ответа с ценой на топливо"""
    id: int
    gas_station_id: int
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Gas Station Photo ====================

class GasStationPhotoBase(BaseModel):
    """Базовая схема фотографии"""
    photo_url: str
    is_main: bool = False
    order: int = 0


class GasStationPhotoCreate(BaseModel):
    """Схема создания фотографии"""
    is_main: bool = False
    order: int = 0


class GasStationPhotoResponse(GasStationPhotoBase):
    """Схема ответа с фотографией"""
    id: int
    gas_station_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Review ====================

class ReviewBase(BaseModel):
    """Базовая схема отзыва"""
    rating: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5")
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    """Схема создания отзыва"""
    pass


class ReviewUpdate(BaseModel):
    """Схема обновления отзыва"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(ReviewBase):
    """Схема ответа с отзывом"""
    id: int
    gas_station_id: int
    user_id: int
    user_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Gas Station ====================

class GasStationBase(BaseModel):
    """Базовая схема заправочной станции"""
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90, description="Широта")
    longitude: float = Field(..., ge=-180, le=180, description="Долгота")
    phone: Optional[str] = None
    is_24_7: bool = False
    working_hours: Optional[str] = None
    category: str = "Заправка"


class GasStationCreate(GasStationBase):
    """Схема создания заправочной станции"""
    fuel_prices: Optional[List[FuelPriceCreate]] = None


class GasStationUpdate(BaseModel):
    """Схема обновления заправочной станции"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    phone: Optional[str] = None
    is_24_7: Optional[bool] = None
    working_hours: Optional[str] = None
    category: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[StationStatusEnum] = None


class GasStationResponse(GasStationBase):
    """Схема ответа с заправочной станцией"""
    id: int
    rating: float
    reviews_count: int
    status: StationStatusEnum
    has_promotions: bool
    fuel_prices: List[FuelPriceResponse] = []
    photos: List[GasStationPhotoResponse] = []
    main_photo: Optional[str] = None  # URL главной фотографии
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class GasStationDetailResponse(GasStationResponse):
    """Детальная схема ответа с заправочной станцией (включая отзывы)"""
    reviews: List[ReviewResponse] = []


class GasStationListResponse(BaseModel):
    """Схема ответа со списком заправочных станций"""
    stations: List[GasStationResponse]
    total: int
    skip: int
    limit: int


# ==================== Filters ====================

class GasStationFilter(BaseModel):
    """Схема фильтрации заправочных станций"""
    fuel_type: Optional[str] = None  # Принимаем строку, конвертируем в enum при необходимости
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    max_price: Optional[float] = Field(None, gt=0)
    is_24_7: Optional[bool] = None
    has_promotions: Optional[bool] = None
    status: Optional[StationStatusEnum] = None
    search_query: Optional[str] = None  # Поиск по названию или адресу
    latitude: Optional[float] = None  # Для поиска по близости
    longitude: Optional[float] = None
    radius_km: Optional[float] = Field(None, gt=0)  # Радиус поиска в километрах


# ==================== Admin ====================

class GasStationAdminUpdate(BaseModel):
    """Схема обновления станции админом"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    phone: Optional[str] = None
    is_24_7: Optional[bool] = None
    working_hours: Optional[str] = None
    category: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[StationStatusEnum] = None


class BulkFuelPriceUpdate(BaseModel):
    """Схема массового обновления цен на топливо"""
    fuel_prices: List[FuelPriceCreate] = Field(..., min_length=1)

