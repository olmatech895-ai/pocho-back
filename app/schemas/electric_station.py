"""
Схемы для электрозаправок
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ConnectorTypeEnum(str, Enum):
    """Типы зарядных разъемов"""
    TYPE_1 = "Type 1"
    TYPE_2 = "Type 2"
    CCS_TYPE_1 = "CCS Type 1"
    CCS_TYPE_2 = "CCS Type 2"
    CHADEMO = "CHAdeMO"
    TESLA_SUPERCHARGER = "Tesla Supercharger"
    TESLA_DESTINATION = "Tesla Destination"
    GB_T = "GB/T"
    OTHER = "Другое"


class ElectricStationStatusEnum(str, Enum):
    """Статус электрозаправки"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ChargingPointStatusEnum(str, Enum):
    """Статус зарядной точки"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    OUT_OF_ORDER = "out_of_order"
    UNKNOWN = "unknown"


# ==================== Charging Point ====================

class ChargingPointBase(BaseModel):
    """Базовая схема зарядной точки"""
    connector_type: ConnectorTypeEnum
    power_kw: float = Field(..., gt=0, description="Мощность в кВт")
    connector_name: Optional[str] = Field(None, max_length=255, description="Название разъема")
    price_per_kwh: Optional[float] = Field(None, gt=0, description="Цена за кВт·ч в сумах")
    price_per_minute: Optional[float] = Field(None, gt=0, description="Цена за минуту в сумах")
    min_price: Optional[float] = Field(None, ge=0, description="Минимальная плата в сумах")
    status: ChargingPointStatusEnum = Field(ChargingPointStatusEnum.UNKNOWN, description="Статус зарядной точки")


class ChargingPointCreate(ChargingPointBase):
    """Схема создания зарядной точки"""
    pass


class ChargingPointUpdate(BaseModel):
    """Схема обновления зарядной точки"""
    connector_type: Optional[ConnectorTypeEnum] = None
    power_kw: Optional[float] = Field(None, gt=0)
    connector_name: Optional[str] = Field(None, max_length=255)
    price_per_kwh: Optional[float] = Field(None, gt=0)
    price_per_minute: Optional[float] = Field(None, gt=0)
    min_price: Optional[float] = Field(None, ge=0)
    status: Optional[ChargingPointStatusEnum] = None


class ChargingPointResponse(ChargingPointBase):
    """Схема ответа с зарядной точкой"""
    id: int
    electric_station_id: int
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Photo ====================

class ElectricStationPhotoBase(BaseModel):
    """Базовая схема фотографии"""
    photo_url: str
    is_main: bool = False
    order: int = 0


class ElectricStationPhotoCreate(BaseModel):
    """Схема создания фотографии"""
    is_main: bool = False
    order: int = 0


class ElectricStationPhotoResponse(ElectricStationPhotoBase):
    """Схема ответа с фотографией"""
    id: int
    electric_station_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Review ====================

class ElectricStationReviewBase(BaseModel):
    """Базовая схема отзыва"""
    rating: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5")
    comment: Optional[str] = None
    charging_speed_rating: Optional[int] = Field(None, ge=1, le=5, description="Оценка скорости зарядки (1-5)")
    price_rating: Optional[int] = Field(None, ge=1, le=5, description="Оценка цены (1-5)")
    location_rating: Optional[int] = Field(None, ge=1, le=5, description="Оценка местоположения (1-5)")


class ElectricStationReviewCreate(ElectricStationReviewBase):
    """Схема создания отзыва"""
    pass


class ElectricStationReviewUpdate(BaseModel):
    """Схема обновления отзыва"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
    charging_speed_rating: Optional[int] = Field(None, ge=1, le=5)
    price_rating: Optional[int] = Field(None, ge=1, le=5)
    location_rating: Optional[int] = Field(None, ge=1, le=5)


class ElectricStationReviewResponse(ElectricStationReviewBase):
    """Схема ответа с отзывом"""
    id: int
    electric_station_id: int
    user_id: int
    user_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Electric Station ====================

class ElectricStationBase(BaseModel):
    """Базовая схема электрозаправки"""
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
    operator: Optional[str] = None
    network: Optional[str] = None
    has_parking: bool = False
    has_waiting_room: bool = False
    has_cafe: bool = False
    has_restroom: bool = False
    accepts_cards: bool = False
    has_mobile_app: bool = False
    requires_membership: bool = False
    category: str = "Электрозаправка"


class ElectricStationCreate(ElectricStationBase):
    """Схема создания электрозаправки"""
    charging_points: Optional[List[ChargingPointCreate]] = None


class ElectricStationUpdate(BaseModel):
    """Схема обновления электрозаправки"""
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
    operator: Optional[str] = None
    network: Optional[str] = None
    has_parking: Optional[bool] = None
    has_waiting_room: Optional[bool] = None
    has_cafe: Optional[bool] = None
    has_restroom: Optional[bool] = None
    accepts_cards: Optional[bool] = None
    has_mobile_app: Optional[bool] = None
    requires_membership: Optional[bool] = None
    category: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[ElectricStationStatusEnum] = None


class ElectricStationResponse(ElectricStationBase):
    """Схема ответа с электрозаправкой"""
    id: int
    total_points: int
    available_points: int
    rating: float
    reviews_count: int
    status: ElectricStationStatusEnum
    has_promotions: bool
    charging_points: List[ChargingPointResponse] = []
    photos: List[ElectricStationPhotoResponse] = []
    main_photo: Optional[str] = None  # URL главной фотографии
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ElectricStationDetailResponse(ElectricStationResponse):
    """Детальная схема ответа с электрозаправкой (включая отзывы)"""
    reviews: List[ElectricStationReviewResponse] = []


class ElectricStationListResponse(BaseModel):
    """Схема ответа со списком электрозаправок"""
    electric_stations: List[ElectricStationResponse]
    total: int
    skip: int
    limit: int


# ==================== Filters ====================

class ElectricStationFilter(BaseModel):
    """Схема фильтрации электрозаправок"""
    connector_type: Optional[str] = None  # Принимаем строку, конвертируем в enum при необходимости
    min_power_kw: Optional[float] = Field(None, gt=0)
    max_power_kw: Optional[float] = Field(None, gt=0)
    min_price_per_kwh: Optional[float] = Field(None, gt=0)
    max_price_per_kwh: Optional[float] = Field(None, gt=0)
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    is_24_7: Optional[bool] = None
    has_promotions: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_waiting_room: Optional[bool] = None
    has_cafe: Optional[bool] = None
    has_restroom: Optional[bool] = None
    accepts_cards: Optional[bool] = None
    has_mobile_app: Optional[bool] = None
    requires_membership: Optional[bool] = None
    has_available_points: Optional[bool] = None  # Есть ли свободные точки
    operator: Optional[str] = None
    network: Optional[str] = None
    status: Optional[ElectricStationStatusEnum] = None
    search_query: Optional[str] = None  # Поиск по названию или адресу
    latitude: Optional[float] = None  # Для поиска по близости
    longitude: Optional[float] = None
    radius_km: Optional[float] = Field(None, gt=0)  # Радиус поиска в километрах


# ==================== Admin ====================

class ElectricStationAdminUpdate(BaseModel):
    """Схема обновления электрозаправки админом"""
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
    operator: Optional[str] = None
    network: Optional[str] = None
    has_parking: Optional[bool] = None
    has_waiting_room: Optional[bool] = None
    has_cafe: Optional[bool] = None
    has_restroom: Optional[bool] = None
    accepts_cards: Optional[bool] = None
    has_mobile_app: Optional[bool] = None
    requires_membership: Optional[bool] = None
    category: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[ElectricStationStatusEnum] = None


class BulkChargingPointUpdate(BaseModel):
    """Схема массового обновления зарядных точек"""
    charging_points: List[ChargingPointCreate] = Field(..., min_length=1)










