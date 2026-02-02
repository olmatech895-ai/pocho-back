"""CRUD доставки: расчёт цены, заказы, баланс, поиск водителя."""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user import User
from app.models.user_extended import UserExtended
from app.models.driver import Driver, DriverStatus
from app.models.delivery import (
    DeliveryTariff,
    DeliveryOrder,
    DeliveryOrderStatus,
    DeliveryOrderStatusHistory,
    UserBalanceLog,
)
from app.schemas.delivery import DeliveryOrderCreate, PointSchema
from app.services.delivery_service.utils import haversine_km, apply_tariff
from app.services.delivery_service.tariff_crud import get_tariff_by_id


def get_active_tariff(db: Session) -> Optional[DeliveryTariff]:
    """Один активный тариф для расчёта (берём первый активный)."""
    return db.query(DeliveryTariff).filter(DeliveryTariff.is_active == True).first()


def calculate_delivery_cost(
    db: Session,
    pickup: PointSchema,
    dropoff: PointSchema,
) -> Tuple[float, float, Optional[DeliveryTariff]]:
    """
    Расчёт стоимости доставки (ТЗ п.2.4, п.3.3).
    Возвращает (distance_km, delivery_cost, tariff).
    """
    # Валидация координат
    if not (-90 <= pickup.latitude <= 90) or not (-180 <= pickup.longitude <= 180):
        raise ValueError(f"Некорректные координаты точки отправления: lat={pickup.latitude}, lon={pickup.longitude}")
    if not (-90 <= dropoff.latitude <= 90) or not (-180 <= dropoff.longitude <= 180):
        raise ValueError(f"Некорректные координаты точки назначения: lat={dropoff.latitude}, lon={dropoff.longitude}")
    
    tariff = get_active_tariff(db)
    if not tariff:
        return 0.0, 0.0, None
    
    # Проверка параметров тарифа
    if tariff.cost_per_km <= 0:
        raise ValueError(f"Некорректный тариф: cost_per_km={tariff.cost_per_km} должен быть > 0")
    if tariff.min_total < 0:
        raise ValueError(f"Некорректный тариф: min_total={tariff.min_total} должен быть >= 0")
    if tariff.base_fixed < 0:
        raise ValueError(f"Некорректный тариф: base_fixed={tariff.base_fixed} должен быть >= 0")
    
    distance_km = haversine_km(
        pickup.latitude, pickup.longitude,
        dropoff.latitude, dropoff.longitude,
    )
    
    if distance_km < 0:
        raise ValueError(f"Отрицательное расстояние: {distance_km}")
    
    cost = apply_tariff(
        distance_km,
        tariff.cost_per_km,
        tariff.min_total,
        tariff.base_fixed,
    )
    
    return distance_km, cost, tariff


def add_status_history(
    db: Session,
    order_id: int,
    from_status: Optional[DeliveryOrderStatus],
    to_status: DeliveryOrderStatus,
    source: str,
) -> None:
    db.add(DeliveryOrderStatusHistory(order_id=order_id, from_status=from_status, to_status=to_status, source=source))


def get_user_balance(db: Session, user_id: int) -> float:
    """Получить баланс пользователя из users_extended (единый баланс)."""
    u = db.query(UserExtended).filter(UserExtended.user_id == user_id).first()
    return float(u.balance) if u else 0.0


def deduct_balance(db: Session, user_id: int, amount: float, order_id: Optional[int], description: str) -> bool:
    """Списание с баланса из users_extended (единый баланс). Не коммитит — вызывающий код коммитит. Возвращает True при успехе."""
    u = db.query(UserExtended).filter(UserExtended.user_id == user_id).with_for_update().first()
    if not u or float(u.balance) < amount:
        return False
    u.balance = float(u.balance) - amount
    db.add(UserBalanceLog(user_id=user_id, order_id=order_id, amount=-amount, type="order_payment", description=description))
    return True


def refund_balance(db: Session, user_id: int, amount: float, order_id: Optional[int], description: str) -> None:
    """Возврат на баланс в users_extended (единый баланс). Не коммитит — вызывающий код коммитит."""
    u = db.query(UserExtended).filter(UserExtended.user_id == user_id).with_for_update().first()
    if u:
        u.balance = float(u.balance) + amount
    db.add(UserBalanceLog(user_id=user_id, order_id=order_id, amount=amount, type="refund", description=description))


def log_balance(db: Session, user_id: int, amount: float, log_type: str, order_id: Optional[int], description: str) -> None:
    """Логирование движения баланса в users_extended (единый баланс)."""
    u = db.query(UserExtended).filter(UserExtended.user_id == user_id).with_for_update().first()
    if u:
        u.balance = float(u.balance) + amount
    db.add(UserBalanceLog(user_id=user_id, order_id=order_id, amount=amount, type=log_type, description=description))


def create_delivery_order(db: Session, user_id: int, data: DeliveryOrderCreate) -> DeliveryOrder:
    """
    Создание заказа (ТЗ п.4): расчёт цены, проверка баланса, создание заказа, списание, переход в searching_driver.
    """
    _, delivery_cost, tariff = calculate_delivery_cost(db, data.pickup, data.dropoff)
    if tariff is None:
        raise ValueError("Нет активного тарифа доставки")
    balance = get_user_balance(db, user_id)
    if balance < delivery_cost:
        raise ValueError("Недостаточно средств на балансе")

    order = DeliveryOrder(
        user_id=user_id,
        tariff_id=tariff.id,
        pickup_latitude=data.pickup.latitude,
        pickup_longitude=data.pickup.longitude,
        pickup_address=data.pickup.address,
        dropoff_latitude=data.dropoff.latitude,
        dropoff_longitude=data.dropoff.longitude,
        dropoff_address=data.dropoff.address,
        parcel_description=data.parcel_description,
        parcel_estimated_value=data.parcel_estimated_value,
        delivery_cost=delivery_cost,
        status=DeliveryOrderStatus.CREATED,
    )
    db.add(order)
    db.flush()
    if not deduct_balance(db, user_id, delivery_cost, order.id, "Оплата заказа доставки"):
        db.rollback()
        raise ValueError("Недостаточно средств на балансе")
    add_status_history(db, order.id, None, DeliveryOrderStatus.CREATED, "system")
    db.commit()
    db.refresh(order)
    return order


def get_delivery_order_by_id(db: Session, order_id: int) -> Optional[DeliveryOrder]:
    return db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()


def get_user_orders(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    status: Optional[DeliveryOrderStatus] = None,
) -> Tuple[List[DeliveryOrder], int]:
    q = db.query(DeliveryOrder).filter(
        DeliveryOrder.user_id == user_id,
        DeliveryOrder.user_id.isnot(None),
        DeliveryOrder.dropoff_latitude.isnot(None),
        DeliveryOrder.dropoff_longitude.isnot(None),
        DeliveryOrder.delivery_cost.isnot(None)
    )
    if status is not None:
        q = q.filter(DeliveryOrder.status == status)
    total = q.count()
    items = q.order_by(DeliveryOrder.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def get_orders_for_driver(
    db: Session,
    driver_id: int,
    skip: int = 0,
    limit: int = 50,
    status: Optional[DeliveryOrderStatus] = None,
) -> Tuple[List[DeliveryOrder], int]:
    q = db.query(DeliveryOrder).filter(
        DeliveryOrder.driver_id == driver_id,
        DeliveryOrder.user_id.isnot(None),
        DeliveryOrder.dropoff_latitude.isnot(None),
        DeliveryOrder.dropoff_longitude.isnot(None),
        DeliveryOrder.delivery_cost.isnot(None)
    )
    if status is not None:
        q = q.filter(DeliveryOrder.status == status)
    total = q.count()
    items = q.order_by(DeliveryOrder.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def find_nearest_available_driver(
    db: Session,
    pickup_lat: float,
    pickup_lng: float,
    limit: int = 10,
) -> List[Driver]:
    """
    Поиск ближайших доступных водителей (ТЗ п.6.1): онлайн, одобрен, с координатами.
    Сортировка по расстоянию до точки забора.
    """
    drivers = (
        db.query(Driver)
        .filter(
            Driver.is_online == True,
            Driver.status == DriverStatus.APPROVED,
            Driver.current_latitude.isnot(None),
            Driver.current_longitude.isnot(None),
        )
        .all()
    )
    with_dist = [(d, haversine_km(pickup_lat, pickup_lng, d.current_latitude or 0, d.current_longitude or 0)) for d in drivers]
    with_dist.sort(key=lambda x: x[1])
    return [d for d, _ in with_dist[:limit]]


def assign_nearest_driver(db: Session, order_id: int) -> Optional[Driver]:
    """
    ТЗ п.6 — назначить ближайшего доступного водителя на заказ.
    Меняет статус на DRIVER_ASSIGNED. Возвращает водителя или None.
    """
    order = get_delivery_order_by_id(db, order_id)
    if not order or order.status != DeliveryOrderStatus.SEARCHING_DRIVER:
        return None
    drivers = find_nearest_available_driver(db, order.pickup_latitude, order.pickup_longitude, limit=1)
    if not drivers:
        return None
    driver = drivers[0]
    order.driver_id = driver.id
    order.status = DeliveryOrderStatus.DRIVER_ASSIGNED
    add_status_history(db, order_id, DeliveryOrderStatus.SEARCHING_DRIVER, DeliveryOrderStatus.DRIVER_ASSIGNED, "system")
    db.commit()
    db.refresh(order)
    return driver


def assign_driver_by_admin(
    db: Session,
    order_id: int,
    driver_id: int,
    admin_user_id: int,
) -> Optional[DeliveryOrder]:
    """
    Назначение водителя администратором на заказ.
    Заказ должен быть в статусе CREATED (без водителя).
    Водитель должен быть одобрен (APPROVED).
    """
    order = get_delivery_order_by_id(db, order_id)
    if not order:
        return None
    if order.status != DeliveryOrderStatus.CREATED:
        raise ValueError(
            f"Назначить водителя можно только для заказа в статусе created. Текущий статус: {order.status.value}"
        )
    if order.driver_id is not None:
        raise ValueError("Водитель уже назначен на этот заказ")

    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise ValueError("Водитель не найден")
    # Допустимые статусы для назначения: APPROVED, ONLINE, OFFLINE (водитель одобрен)
    assignable_statuses = (DriverStatus.APPROVED, DriverStatus.ONLINE, DriverStatus.OFFLINE)
    if driver.status not in assignable_statuses:
        raise ValueError(
            f"Водитель не может быть назначен (статус: {driver.status.value}). "
            f"Допустимые: approved, online, offline"
        )

    old_status = order.status
    order.driver_id = driver_id
    order.status = DeliveryOrderStatus.DRIVER_ASSIGNED
    add_status_history(db, order_id, old_status, DeliveryOrderStatus.DRIVER_ASSIGNED, "admin")
    db.commit()
    db.refresh(order)
    return order


def unassign_driver(db: Session, order_id: int) -> Optional[DeliveryOrder]:
    """Снять водителя с заказа (при отказе), вернуть статус CREATED для повторного назначения администратором."""
    order = get_delivery_order_by_id(db, order_id)
    if not order:
        return None
    old = order.status
    order.driver_id = None
    order.status = DeliveryOrderStatus.CREATED
    add_status_history(db, order_id, old, DeliveryOrderStatus.CREATED, "driver")
    db.commit()
    db.refresh(order)
    return order


def update_order_status(
    db: Session,
    order_id: int,
    new_status: DeliveryOrderStatus,
    source: str,
) -> Optional[DeliveryOrder]:
    order = get_delivery_order_by_id(db, order_id)
    if not order:
        return None
    old = order.status
    order.status = new_status
    add_status_history(db, order_id, old, new_status, source)
    db.commit()
    db.refresh(order)
    return order


def cancel_order(
    db: Session,
    order_id: int,
    canceled_by_user_id: int,
    reason: Optional[str],
    refund: bool = True,
    source: str = "user",
) -> Optional[DeliveryOrder]:
    """
    Отмена заказа (ТЗ п.8). При refund=True возвращаем средства на баланс.
    source: "user" или "admin".
    """
    from datetime import datetime
    order = get_delivery_order_by_id(db, order_id)
    if not order:
        return None
    if order.status == DeliveryOrderStatus.CANCELED:
        return order
    old_status = order.status
    order.status = DeliveryOrderStatus.CANCELED
    order.canceled_at = datetime.utcnow()
    order.cancel_reason = reason
    order.canceled_by_user_id = canceled_by_user_id
    add_status_history(db, order_id, old_status, DeliveryOrderStatus.CANCELED, source)
    if refund and order.delivery_cost and order.user_id:
        refund_balance(db, order.user_id, order.delivery_cost, order.id, "Возврат за отмену заказа")
    db.commit()
    db.refresh(order)
    return order
