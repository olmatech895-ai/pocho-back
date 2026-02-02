"""
Схемы Pydantic для системы водителей
"""
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from app.models.driver import (
    DriverStatus,
    DocumentType,
    DocumentStatus,
    VehicleType
)


# ==================== Driver Schemas ====================

class DriverBase(BaseModel):
    """Базовая схема водителя"""
    full_name: str = Field(..., min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    region_id: Optional[int] = None


class DriverCreate(DriverBase):
    """Схема создания водителя"""
    phone_number: str = Field(..., min_length=9, max_length=20)


class DriverCreateByAdmin(DriverBase):
    """Схема создания водителя администратором"""
    user_id: int = Field(..., description="ID пользователя")
    phone_number: str = Field(..., min_length=9, max_length=20)
    status: Optional[DriverStatus] = Field(DriverStatus.PENDING, description="Начальный статус водителя")


class AssignDriverRequest(BaseModel):
    """Схема назначения пользователя водителем (админ)"""
    user_id: int = Field(..., description="ID пользователя для назначения водителем")
    full_name: Optional[str] = Field(None, min_length=2, max_length=200, description="Полное имя водителя (если не указано, используется имя пользователя)")
    region_id: Optional[int] = Field(None, description="ID региона")
    status: Optional[DriverStatus] = Field(DriverStatus.PENDING, description="Начальный статус водителя")


class DriverUpdate(BaseModel):
    """Схема обновления водителя"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    region_id: Optional[int] = None
    photo_url: Optional[str] = None
    auto_accept_orders: Optional[bool] = None


class DriverResponse(DriverBase):
    """Схема ответа с данными водителя"""
    id: int
    user_id: int
    phone_number: str
    photo_url: Optional[str] = None
    status: DriverStatus
    rating: float
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    balance: float
    total_earnings: float
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    is_online: bool
    auto_accept_orders: bool
    admin_comment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DriverStatusUpdate(BaseModel):
    """Схема обновления статуса водителя"""
    status: DriverStatus
    admin_comment: Optional[str] = None


class DriverOnlineStatus(BaseModel):
    """Схема статуса онлайн/оффлайн"""
    is_online: bool


# ==================== Driver Document Schemas ====================

class DriverDocumentBase(BaseModel):
    """Базовая схема документа водителя"""
    document_type: DocumentType
    document_number: Optional[str] = None
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None


class DriverDocumentCreate(DriverDocumentBase):
    """Схема создания документа"""
    front_image_url: str
    back_image_url: Optional[str] = None


class DriverDocumentUpdate(BaseModel):
    """Схема обновления документа"""
    front_image_url: Optional[str] = None
    back_image_url: Optional[str] = None
    document_number: Optional[str] = None
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None


class DriverDocumentResponse(DriverDocumentBase):
    """Схема ответа с данными документа"""
    id: int
    driver_id: int
    front_image_url: Optional[str] = None
    back_image_url: Optional[str] = None
    status: DocumentStatus
    admin_comment: Optional[str] = None
    uploaded_at: datetime
    verified_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DriverDocumentStatusUpdate(BaseModel):
    """Схема обновления статуса документа"""
    status: DocumentStatus
    admin_comment: Optional[str] = None


# ==================== Vehicle Schemas ====================

class VehicleBase(BaseModel):
    """Базовая схема транспортного средства"""
    vehicle_type: VehicleType
    brand: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    color: Optional[str] = Field(None, max_length=50)
    license_plate: str = Field(..., min_length=1, max_length=20)
    vehicle_passport_number: Optional[str] = None
    capacity_kg: Optional[float] = Field(None, ge=0)
    volume_m3: Optional[float] = Field(None, ge=0)


class VehicleCreate(VehicleBase):
    """Схема создания ТС"""
    photo_url: Optional[str] = None


class VehicleUpdate(BaseModel):
    """Схема обновления ТС"""
    brand: Optional[str] = Field(None, min_length=1, max_length=100)
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    color: Optional[str] = Field(None, max_length=50)
    license_plate: Optional[str] = Field(None, min_length=1, max_length=20)
    vehicle_passport_number: Optional[str] = None
    photo_url: Optional[str] = None
    capacity_kg: Optional[float] = Field(None, ge=0)
    volume_m3: Optional[float] = Field(None, ge=0)


class VehicleResponse(VehicleBase):
    """Схема ответа с данными ТС"""
    id: int
    driver_id: int
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Region Schemas ====================

class RegionBase(BaseModel):
    """Базовая схема региона"""
    name_uz: str = Field(..., min_length=1, max_length=200)
    name_ru: str = Field(..., min_length=1, max_length=200)
    name_en: Optional[str] = Field(None, max_length=200)
    center_latitude: Optional[float] = Field(None, ge=-90, le=90)
    center_longitude: Optional[float] = Field(None, ge=-180, le=180)
    display_order: int = 0


class RegionCreate(RegionBase):
    """Схема создания региона"""
    is_active: bool = True


class RegionUpdate(BaseModel):
    """Схема обновления региона"""
    name_uz: Optional[str] = Field(None, min_length=1, max_length=200)
    name_ru: Optional[str] = Field(None, min_length=1, max_length=200)
    name_en: Optional[str] = Field(None, max_length=200)
    center_latitude: Optional[float] = Field(None, ge=-90, le=90)
    center_longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class RegionResponse(RegionBase):
    """Схема ответа с данными региона"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== Driver Statistics ====================

class DriverStatistics(BaseModel):
    """Статистика водителя"""
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    rating: float
    total_earnings: float
    balance: float
    online_hours_today: Optional[float] = None
    orders_today: int = 0
    earnings_today: float = 0.0



