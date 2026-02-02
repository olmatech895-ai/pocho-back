"""
Схемы для расширенной модели пользователя
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


# ==================== User Extended ====================

class UserExtendedBase(BaseModel):
    """Базовая схема пользователя"""
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    language: str = "ru"
    balance: float = 0.0
    level: str = "Новичок"
    rating: float = 0.0


class UserExtendedCreate(UserExtendedBase):
    """Схема создания пользователя"""
    user_id: int


class UserExtendedUpdate(BaseModel):
    """Схема обновления пользователя"""
    name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    language: Optional[str] = None
    balance: Optional[float] = None
    level: Optional[str] = None
    rating: Optional[float] = None


class UserExtendedResponse(UserExtendedBase):
    """Схема ответа пользователя"""
    id: int
    user_id: int
    total_stations_visited: int
    total_spent: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Profile ====================

class DocumentInfo(BaseModel):
    """Информация о документе"""
    image_url: Optional[str] = None
    verified: bool = False
    uploaded_at: Optional[datetime] = None


class ProfileDocuments(BaseModel):
    """Документы пользователя"""
    passport: Optional[DocumentInfo] = None
    driving_license: Optional[DocumentInfo] = None


class ProfileSettings(BaseModel):
    """Настройки профиля"""
    notifications_enabled: bool = True
    language: str = "ru"


class UserProfileResponse(BaseModel):
    """Схема ответа профиля"""
    id: int
    user_id: int
    documents: Optional[ProfileDocuments] = None
    settings: ProfileSettings
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Схема обновления профиля"""
    passport_image_url: Optional[str] = None
    passport_verified: Optional[bool] = None
    passport_uploaded_at: Optional[datetime] = None
    driving_license_image_url: Optional[str] = None
    driving_license_verified: Optional[bool] = None
    driving_license_uploaded_at: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None


class UpdateNameRequest(BaseModel):
    """Схема обновления имени пользователя"""
    name: str = Field(..., min_length=1, max_length=100, description="Имя пользователя")


class UpdateEmailRequest(BaseModel):
    """Схема обновления email пользователя"""
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", description="Email адрес")


class UpdateNotificationsRequest(BaseModel):
    """Схема обновления настроек уведомлений"""
    notifications_enabled: bool


class UpdateResponse(BaseModel):
    """Схема ответа на обновление"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ==================== Favorites ====================

class UserFavoriteCreate(BaseModel):
    """Схема создания избранного"""
    favorite_type: str = Field(..., description="fuel_station, restaurant, car_service, car_wash, charging_station")
    place_id: int
    extra_data: Optional[Dict[str, Any]] = None


class UserFavoriteResponse(BaseModel):
    """Схема ответа избранного"""
    id: int
    user_id: int
    favorite_type: str
    place_id: int
    extra_data: Optional[Dict[str, Any]] = None
    added_at: datetime

    class Config:
        from_attributes = True


class FavoritesListResponse(BaseModel):
    """Схема списка избранного"""
    fuel_stations: List[UserFavoriteResponse] = []
    restaurants: List[UserFavoriteResponse] = []
    car_services: List[UserFavoriteResponse] = []
    car_washes: List[UserFavoriteResponse] = []
    charging_stations: List[UserFavoriteResponse] = []


# ==================== Achievements ====================

class UserAchievementResponse(BaseModel):
    """Схема ответа достижения пользователя"""
    id: int
    user_id: int
    achievement_type: str  # Тип достижения (например: "first_refuel", "star_driver", "lover", "premium")
    unlocked: bool  # Статус: true - разблокировано, false - заблокировано
    unlocked_at: Optional[datetime] = None
    icon: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserAchievementCreate(BaseModel):
    """Схема создания достижения"""
    achievement_type: str
    icon: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[int] = None


class UserAchievementUpdate(BaseModel):
    """Схема обновления достижения"""
    unlocked: Optional[bool] = None
    unlocked_at: Optional[datetime] = None
    icon: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[int] = None


# ==================== Notifications ====================

class UserNotificationResponse(BaseModel):
    """Схема ответа настроек уведомлений"""
    id: int
    user_id: int
    enabled: bool
    price_alerts: bool
    new_stations: bool
    promotions: bool
    reviews: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserNotificationUpdate(BaseModel):
    """Схема обновления уведомлений"""
    enabled: Optional[bool] = None
    price_alerts: Optional[bool] = None
    new_stations: Optional[bool] = None
    promotions: Optional[bool] = None
    reviews: Optional[bool] = None


# ==================== Transactions ====================

class TransactionCreate(BaseModel):
    """Схема создания транзакции"""
    type: str = Field(..., description="top_up, purchase, refund, bonus")
    amount: float
    description: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class TransactionResponse(BaseModel):
    """Схема ответа транзакции"""
    id: int
    user_id: int
    type: str
    amount: float
    description: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Statistics ====================

class UserStatisticsResponse(BaseModel):
    """Схема ответа статистики"""
    id: int
    user_id: int
    favorite_fuel_stations_count: int
    favorite_restaurants_count: int
    favorite_car_services_count: int
    favorite_car_washes_count: int
    favorite_charging_stations_count: int
    total_favorites_count: int
    total_spent: float
    average_rating_given: float
    reviews_written: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Full User Response ====================

class FullUserResponse(BaseModel):
    """Полная схема пользователя со всеми данными"""
    user: UserExtendedResponse
    profile: Optional[UserProfileResponse] = None
    favorites: FavoritesListResponse
    statistics: Optional[UserStatisticsResponse] = None
    achievements: List[UserAchievementResponse] = []
    notifications: Optional[UserNotificationResponse] = None
    transactions: List[TransactionResponse] = []


# ==================== Profile with User Data ====================

class BalanceInfo(BaseModel):
    """Информация о балансе пользователя для отображения"""
    amount: float = 0.0
    currency: str = "сум"
    formatted: str = "0 сум"  # Форматированная строка для отображения
    
    @classmethod
    def from_amount(cls, amount: float, currency: str = "сум") -> "BalanceInfo":
        """Создание объекта баланса с форматированием"""
        # Форматируем число с разделителями тысяч
        if amount >= 1000000:
            formatted = f"{amount / 1000000:.1f} млн {currency}"
        elif amount >= 1000:
            formatted = f"{amount / 1000:.1f} тыс {currency}"
        else:
            formatted = f"{int(amount)} {currency}"
        
        return cls(
            amount=amount,
            currency=currency,
            formatted=formatted
        )


class ProfileWithUserDataResponse(BaseModel):
    """Схема профиля с данными пользователя (для эндпоинта /profile)"""
    id: int
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    language: str = "ru"
    balance: float = 0.0
    balance_info: Optional[BalanceInfo] = None  # Дополнительная информация о балансе для стилизации
    level: str = "Новичок"
    rating: float = 0.0
    total_stations_visited: int = 0
    total_spent: float = 0.0
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True