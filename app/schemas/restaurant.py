"""
Схемы для ресторанов
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class CuisineTypeEnum(str, Enum):
    """Типы кухни"""
    UZBEK = "Узбекская"
    RUSSIAN = "Русская"
    EUROPEAN = "Европейская"
    ASIAN = "Азиатская"
    ITALIAN = "Итальянская"
    JAPANESE = "Японская"
    CHINESE = "Китайская"
    AMERICAN = "Американская"
    FAST_FOOD = "Фастфуд"
    PIZZA = "Пицца"
    SUSHI = "Суши"
    GRILL = "Гриль"
    VEGETARIAN = "Вегетарианская"
    OTHER = "Другая"


class RestaurantStatusEnum(str, Enum):
    """Статус ресторана"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


# ==================== Menu Item ====================

class MenuItemBase(BaseModel):
    """Базовая схема блюда"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0, description="Цена в сумах")
    image_url: Optional[str] = None
    is_available: bool = True
    weight: Optional[str] = None
    calories: Optional[int] = Field(None, ge=0)
    order: int = 0


class MenuItemCreate(MenuItemBase):
    """Схема создания блюда"""
    pass


class MenuItemUpdate(BaseModel):
    """Схема обновления блюда"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    weight: Optional[str] = None
    calories: Optional[int] = Field(None, ge=0)
    order: Optional[int] = None


class MenuItemResponse(MenuItemBase):
    """Схема ответа с блюдом"""
    id: int
    category_id: int
    restaurant_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Menu Category ====================

class MenuCategoryBase(BaseModel):
    """Базовая схема категории меню"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    order: int = 0


class MenuCategoryCreate(MenuCategoryBase):
    """Схема создания категории меню"""
    items: Optional[List[MenuItemCreate]] = None


class MenuCategoryUpdate(BaseModel):
    """Схема обновления категории меню"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    order: Optional[int] = None


class MenuCategoryResponse(MenuCategoryBase):
    """Схема ответа с категорией меню"""
    id: int
    restaurant_id: int
    items: List[MenuItemResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Restaurant Photo ====================

class RestaurantPhotoBase(BaseModel):
    """Базовая схема фотографии"""
    photo_url: str
    is_main: bool = False
    order: int = 0


class RestaurantPhotoCreate(BaseModel):
    """Схема создания фотографии"""
    is_main: bool = False
    order: int = 0


class RestaurantPhotoResponse(RestaurantPhotoBase):
    """Схема ответа с фотографией"""
    id: int
    restaurant_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Review ====================

class RestaurantReviewBase(BaseModel):
    """Базовая схема отзыва"""
    rating: int = Field(..., ge=1, le=5, description="Рейтинг от 1 до 5")
    comment: Optional[str] = None


class RestaurantReviewCreate(RestaurantReviewBase):
    """Схема создания отзыва"""
    pass


class RestaurantReviewUpdate(BaseModel):
    """Схема обновления отзыва"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class RestaurantReviewResponse(RestaurantReviewBase):
    """Схема ответа с отзывом"""
    id: int
    restaurant_id: int
    user_id: int
    user_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Restaurant ====================

class RestaurantBase(BaseModel):
    """Базовая схема ресторана"""
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90, description="Широта")
    longitude: float = Field(..., ge=-180, le=180, description="Долгота")
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    is_24_7: bool = False
    working_hours: Optional[str] = None
    cuisine_type: CuisineTypeEnum
    average_check: Optional[float] = Field(None, gt=0, description="Средний чек в сумах")
    has_booking: bool = False
    has_delivery: bool = False
    has_parking: bool = False
    has_wifi: bool = False
    category: str = "Ресторан"
    description: Optional[str] = None


class RestaurantCreate(RestaurantBase):
    """Схема создания ресторана"""
    menu_categories: Optional[List[MenuCategoryCreate]] = None


class RestaurantUpdate(BaseModel):
    """Схема обновления ресторана"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    is_24_7: Optional[bool] = None
    working_hours: Optional[str] = None
    cuisine_type: Optional[CuisineTypeEnum] = None
    average_check: Optional[float] = Field(None, gt=0)
    has_booking: Optional[bool] = None
    has_delivery: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_wifi: Optional[bool] = None
    category: Optional[str] = None
    description: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[RestaurantStatusEnum] = None


class RestaurantResponse(RestaurantBase):
    """Схема ответа с рестораном"""
    id: int
    rating: float
    reviews_count: int
    status: RestaurantStatusEnum
    has_promotions: bool
    menu_categories: List[MenuCategoryResponse] = []
    photos: List[RestaurantPhotoResponse] = []
    main_photo: Optional[str] = None  # URL главной фотографии
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class RestaurantDetailResponse(RestaurantResponse):
    """Детальная схема ответа с рестораном (включая отзывы)"""
    reviews: List[RestaurantReviewResponse] = []


class RestaurantListResponse(BaseModel):
    """Схема ответа со списком ресторанов"""
    restaurants: List[RestaurantResponse]
    total: int
    skip: int
    limit: int


# ==================== Filters ====================

class RestaurantFilter(BaseModel):
    """Схема фильтрации ресторанов"""
    cuisine_type: Optional[str] = None  # Принимаем строку, конвертируем в enum при необходимости
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    max_average_check: Optional[float] = Field(None, gt=0)
    min_average_check: Optional[float] = Field(None, gt=0)
    is_24_7: Optional[bool] = None
    has_promotions: Optional[bool] = None
    has_booking: Optional[bool] = None
    has_delivery: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_wifi: Optional[bool] = None
    status: Optional[RestaurantStatusEnum] = None
    search_query: Optional[str] = None  # Поиск по названию или адресу
    latitude: Optional[float] = None  # Для поиска по близости
    longitude: Optional[float] = None
    radius_km: Optional[float] = Field(None, gt=0)  # Радиус поиска в километрах


# ==================== Admin ====================

class RestaurantAdminUpdate(BaseModel):
    """Схема обновления ресторана админом"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    is_24_7: Optional[bool] = None
    working_hours: Optional[str] = None
    cuisine_type: Optional[CuisineTypeEnum] = None
    average_check: Optional[float] = Field(None, gt=0)
    has_booking: Optional[bool] = None
    has_delivery: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_wifi: Optional[bool] = None
    category: Optional[str] = None
    description: Optional[str] = None
    has_promotions: Optional[bool] = None
    status: Optional[RestaurantStatusEnum] = None











