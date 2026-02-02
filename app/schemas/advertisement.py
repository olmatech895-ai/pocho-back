"""
Схемы для рекламных блоков
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class AdvertisementTypeEnum(str, Enum):
    """Тип рекламного блока"""
    BANNER = "banner"
    PROMO = "promo"
    NOTIFICATION = "notification"
    POPUP = "popup"
    CARD = "card"


class AdvertisementStatusEnum(str, Enum):
    """Статус рекламы"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class AdvertisementPositionEnum(str, Enum):
    """Позиция рекламы в приложении"""
    HOME_TOP = "home_top"
    HOME_BOTTOM = "home_bottom"
    GAS_STATIONS_LIST = "gas_stations_list"
    RESTAURANTS_LIST = "restaurants_list"
    SERVICE_STATIONS_LIST = "service_stations_list"
    CAR_WASHES_LIST = "car_washes_list"
    PROFILE = "profile"
    GLOBAL_CHAT = "global_chat"
    OTHER = "other"


# ==================== Advertisement View ====================

class AdvertisementViewBase(BaseModel):
    """Базовая схема просмотра"""
    pass


class AdvertisementViewCreate(BaseModel):
    """Схема создания просмотра"""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    app_version: Optional[str] = None


class AdvertisementViewResponse(BaseModel):
    """Схема ответа с просмотром"""
    id: int
    advertisement_id: int
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    app_version: Optional[str] = None
    viewed_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Advertisement Click ====================

class AdvertisementClickCreate(BaseModel):
    """Схема создания клика"""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None


class AdvertisementClickResponse(BaseModel):
    """Схема ответа с кликом"""
    id: int
    advertisement_id: int
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    clicked_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Advertisement ====================

class AdvertisementBase(BaseModel):
    """Базовая схема рекламы"""
    title: str = Field(..., min_length=1, max_length=255, description="Заголовок рекламы")
    description: Optional[str] = Field(None, description="Описание/текст рекламы")
    image_url: str = Field(..., description="URL изображения рекламы")
    link_url: Optional[str] = Field(None, description="URL для перехода при клике")
    link_type: Optional[str] = Field(None, description="Тип ссылки (internal, external, deep_link)")
    ad_type: AdvertisementTypeEnum = Field(AdvertisementTypeEnum.BANNER, description="Тип рекламного блока")
    position: AdvertisementPositionEnum = Field(AdvertisementPositionEnum.HOME_TOP, description="Позиция в приложении")
    status: AdvertisementStatusEnum = Field(AdvertisementStatusEnum.ACTIVE, description="Статус рекламы")
    is_active: bool = Field(True, description="Активна ли реклама")
    start_date: Optional[datetime] = Field(None, description="Дата начала показа")
    end_date: Optional[datetime] = Field(None, description="Дата окончания показа")
    priority: int = Field(0, description="Приоритет показа (больше = выше)")
    display_order: int = Field(0, description="Порядок отображения")
    target_audience: Optional[str] = Field(None, description="Целевая аудитория")
    show_conditions: Optional[str] = Field(None, description="JSON с условиями показа")


class AdvertisementCreate(AdvertisementBase):
    """Схема создания рекламы"""
    pass


class AdvertisementUpdate(BaseModel):
    """Схема обновления рекламы"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    link_type: Optional[str] = None
    ad_type: Optional[AdvertisementTypeEnum] = None
    position: Optional[AdvertisementPositionEnum] = None
    status: Optional[AdvertisementStatusEnum] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: Optional[int] = None
    display_order: Optional[int] = None
    target_audience: Optional[str] = None
    show_conditions: Optional[str] = None


class AdvertisementResponse(AdvertisementBase):
    """Схема ответа с рекламой"""
    id: int
    views_count: int
    clicks_count: int
    created_by_admin_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AdvertisementDetailResponse(AdvertisementResponse):
    """Детальная схема ответа с рекламой (включая статистику)"""
    recent_views: Optional[List[AdvertisementViewResponse]] = []
    recent_clicks: Optional[List[AdvertisementClickResponse]] = []


class AdvertisementListResponse(BaseModel):
    """Схема ответа со списком рекламы"""
    advertisements: List[AdvertisementResponse]
    total: int
    skip: int
    limit: int


# ==================== Filters ====================

class AdvertisementFilter(BaseModel):
    """Схема фильтрации рекламы"""
    ad_type: Optional[AdvertisementTypeEnum] = None
    position: Optional[AdvertisementPositionEnum] = None
    status: Optional[AdvertisementStatusEnum] = None
    is_active: Optional[bool] = None
    target_audience: Optional[str] = None
    search_query: Optional[str] = None  # Поиск по названию или описанию


# ==================== Statistics ====================

class AdvertisementStatisticsResponse(BaseModel):
    """Схема статистики рекламы"""
    advertisement_id: int
    title: str
    views_count: int
    clicks_count: int
    click_through_rate: float  # CTR в процентах
    unique_views: int  # Уникальные просмотры (по пользователям)
    unique_clicks: int  # Уникальные клики (по пользователям)
    views_today: int
    clicks_today: int
    views_this_week: int
    clicks_this_week: int
    views_this_month: int
    clicks_this_month: int


# ==================== Client ====================

class AdvertisementForClientResponse(BaseModel):
    """Схема рекламы для клиентского приложения (только активные)"""
    id: int
    title: str
    description: Optional[str] = None
    image_url: str
    link_url: Optional[str] = None
    link_type: Optional[str] = None
    ad_type: AdvertisementTypeEnum
    position: AdvertisementPositionEnum
    priority: int
    display_order: int
    
    class Config:
        from_attributes = True










