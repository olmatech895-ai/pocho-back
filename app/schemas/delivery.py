"""
Схемы Pydantic для доставки по ТЗ.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from app.models.delivery import DeliveryOrderStatus


# --- Точка (ТЗ п.1) ---
class PointSchema(BaseModel):
    """Точка: координаты и описание"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)


# --- Расчёт стоимости (ТЗ п.2.4, п.3) ---
class PriceCalculationRequest(BaseModel):
    """Запрос на расчёт стоимости доставки"""
    pickup: PointSchema
    dropoff: PointSchema


class PriceCalculationResponse(BaseModel):
    """Ответ: рассчитанная стоимость"""
    distance_km: float
    delivery_cost: float
    min_total: float
    cost_per_km: float
    base_fixed: float


# --- Тарифы (админ) ---
class DeliveryTariffBase(BaseModel):
    name: Optional[str] = None
    cost_per_km: float = Field(..., gt=0)
    min_total: float = Field(..., ge=0)
    base_fixed: float = Field(0, ge=0)
    extra_coefficients: Optional[str] = None  # JSON строка
    is_active: bool = True


class DeliveryTariffCreate(DeliveryTariffBase):
    pass


class DeliveryTariffUpdate(BaseModel):
    name: Optional[str] = None
    cost_per_km: Optional[float] = Field(None, gt=0)
    min_total: Optional[float] = Field(None, ge=0)
    base_fixed: Optional[float] = Field(None, ge=0)
    extra_coefficients: Optional[str] = None
    is_active: Optional[bool] = None


class DeliveryTariffResponse(BaseModel):
    id: int
    name: Optional[str] = None
    cost_per_km: float
    min_total: float
    base_fixed: float
    extra_coefficients: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Заказ (ТЗ п.2–4) ---
class DeliveryOrderCreate(BaseModel):
    """Создание заказа: точки, описание посылки (ТЗ п.2)"""
    pickup: PointSchema
    dropoff: PointSchema
    parcel_description: Optional[str] = None
    parcel_estimated_value: Optional[float] = Field(None, ge=0)


class DeliveryOrderResponse(BaseModel):
    id: int
    user_id: int
    driver_id: Optional[int] = None
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: Optional[str] = None
    dropoff_latitude: float
    dropoff_longitude: float
    dropoff_address: Optional[str] = None
    parcel_description: Optional[str] = None
    parcel_estimated_value: Optional[float] = None
    delivery_cost: float
    status: DeliveryOrderStatus
    canceled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Доп. поля для отображения
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None

    class Config:
        from_attributes = True


class DeliveryOrderStatusUpdate(BaseModel):
    """Смена статуса (водитель/админ)"""
    status: DeliveryOrderStatus


class DeliveryOrderListResponse(BaseModel):
    """Список заказов с пагинацией"""
    items: List[DeliveryOrderResponse]
    total: int
    skip: int
    limit: int


# --- Баланс (ТЗ п.5) ---
class UserBalanceResponse(BaseModel):
    balance: float


class UserBalanceLogResponse(BaseModel):
    id: int
    order_id: Optional[int] = None
    amount: float
    type: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Назначение водителя (админ) ---
class AssignDriverRequest(BaseModel):
    """Запрос на назначение водителя администратором"""
    driver_id: int = Field(..., gt=0, description="ID водителя")


# --- Отмена (ТЗ п.8) ---
class OrderCancelRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)
