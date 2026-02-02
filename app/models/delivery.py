"""
Модели доставки по ТЗ: тарифы, заказы, статусы, баланс.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum as SQLEnum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import TypeDecorator
import enum

from app.database import Base


class DeliveryOrderStatus(str, enum.Enum):
    """Статусы заказа доставки по ТЗ"""
    CREATED = "created"                    # Заказ создан, водитель не назначен
    SEARCHING_DRIVER = "searching_driver"  # Идёт поиск водителя
    DRIVER_ASSIGNED = "driver_assigned"    # Водитель назначен
    DRIVER_ON_WAY = "driver_on_way"        # Водитель едет к точке забора
    PICKED_UP = "picked_up"                # Посылка получена водителем
    IN_DELIVERY = "in_delivery"            # Посылка в доставке
    DELIVERED = "delivered"                # Посылка доставлена
    COMPLETED = "completed"                # Заказ завершён
    CANCELED = "canceled"                  # Заказ отменён


# Нормализация значений из БД: приводим к нижнему регистру и обрабатываем варианты написания
def _status_from_db(value):
    if value is None:
        return None
    if isinstance(value, DeliveryOrderStatus):
        return value
    if not isinstance(value, str):
        return DeliveryOrderStatus(value)
    
    value_clean = value.strip()
    
    # Маппинг вариантов написания (особенно для отмены)
    status_map = {
        "cancelled": "canceled",  # Британское написание -> американское
        "CANCELLED": "canceled",  # Верхний регистр
    }
    
    # Если есть маппинг, используем его
    if value_clean in status_map:
        value_clean = status_map[value_clean]
    
    # Приводим к нижнему регистру для нормализации
    normalized = value_clean.lower()
    
    # Пытаемся найти в enum по нормализованному значению (enum хранит значения в нижнем регистре)
    try:
        return DeliveryOrderStatus(normalized)
    except ValueError:
        # Если не получилось, пробуем найти по имени enum (для совместимости со старыми данными)
        # Например, если в БД хранится имя enum "DELIVERED" вместо значения "delivered"
        value_upper = value_clean.upper()
        for status in DeliveryOrderStatus:
            if status.name.upper() == value_upper:
                return status
        # Если ничего не подошло, пробрасываем ошибку
        raise ValueError(f"Unknown status value: {value}")


class DeliveryOrderStatusType(TypeDecorator):
    """Тип колонки статуса: при чтении из БД CANCELLED/cancelled отображаются в CANCELED."""
    impl = String(50)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, DeliveryOrderStatus):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return _status_from_db(value)


class DeliveryTariff(Base):
    """Тариф доставки (настраивается администратором)"""
    __tablename__ = "delivery_tariffs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=True)  # Название для админки

    # Параметры расчёта (ТЗ п.3.2)
    cost_per_km = Column(Float, nullable=False)       # Стоимость за км
    min_total = Column(Float, nullable=False)         # Минимальная стоимость доставки
    base_fixed = Column(Float, default=0.0, nullable=False)  # Фиксированная базовая стоимость
    # Доп. коэффициенты — JSON, например {"peak_hour": 1.2}
    extra_coefficients = Column(Text, nullable=True)   # JSON, опционально

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DeliveryOrder(Base):
    """Заказ на доставку"""
    __tablename__ = "delivery_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True, index=True)
    tariff_id = Column(Integer, ForeignKey("delivery_tariffs.id"), nullable=True, index=True)
    # Старая колонка для совместимости (nullable, не используется в коде)
    customer_id = Column(Integer, nullable=True)

    # Точка отправления (ТЗ п.2.1)
    pickup_latitude = Column(Float, nullable=False)
    pickup_longitude = Column(Float, nullable=False)
    pickup_address = Column(String(500), nullable=True)  # Адрес/описание

    # Точка назначения (ТЗ п.2.2)
    dropoff_latitude = Column(Float, nullable=False)
    dropoff_longitude = Column(Float, nullable=False)
    dropoff_address = Column(String(500), nullable=True)
    # Старые колонки для совместимости (nullable, не используются в коде)
    delivery_address = Column(String(500), nullable=True)
    delivery_latitude = Column(Float, nullable=True)
    delivery_longitude = Column(Float, nullable=True)

    # Описание посылки (ТЗ п.2.3)
    parcel_description = Column(Text, nullable=True)
    parcel_estimated_value = Column(Float, nullable=True)  # Примерная стоимость посылки

    # Стоимость и статус
    delivery_cost = Column(Float, nullable=False)  # Итоговая стоимость доставки
    status = Column(DeliveryOrderStatusType, default=DeliveryOrderStatus.CREATED, nullable=False, index=True)

    # Отмена (ТЗ п.8)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    canceled_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # user или admin

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    driver = relationship("Driver", foreign_keys=[driver_id])
    tariff = relationship("DeliveryTariff", foreign_keys=[tariff_id])
    status_history = relationship("DeliveryOrderStatusHistory", back_populates="order", order_by="DeliveryOrderStatusHistory.created_at")


class DeliveryOrderStatusHistory(Base):
    """История смены статусов заказа (ТЗ п.7 — каждый переход фиксируется)"""
    __tablename__ = "delivery_order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("delivery_orders.id"), nullable=False, index=True)
    from_status = Column(DeliveryOrderStatusType, nullable=True)
    to_status = Column(DeliveryOrderStatusType, nullable=False)
    source = Column(String(50), nullable=True)  # user, driver, admin, system
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("DeliveryOrder", back_populates="status_history")


class UserBalanceLog(Base):
    """Движения по балансу пользователя (доставка: списание, возврат)"""
    __tablename__ = "user_balance_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("delivery_orders.id"), nullable=True, index=True)

    amount = Column(Float, nullable=False)  # Отрицательное — списание, положительное — возврат
    type = Column(String(50), nullable=False, index=True)  # order_payment, refund, admin_adjustment
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
    order = relationship("DeliveryOrder", foreign_keys=[order_id])

    __table_args__ = (Index("idx_balance_log_user_created", "user_id", "created_at"),)
