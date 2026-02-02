"""
API доставки для водителя: заказы, принять/отклонить, смена статуса (ТЗ п.6, п.7).
"""
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.driver import Driver
from app.models.delivery import DeliveryOrderStatus
from app.schemas.delivery import DeliveryOrderResponse, DeliveryOrderListResponse, DeliveryOrderStatusUpdate
from app.services.delivery_service.crud import (
    get_delivery_order_by_id,
    get_orders_for_driver,
    update_order_status,
    unassign_driver,
)
from app.services.driver_service.crud import get_driver_by_user_id

router = APIRouter(prefix="/delivery/driver", tags=["Доставка: Водитель"])


def get_current_driver(user: Annotated[User, Depends(get_current_active_user)], db: Annotated[Session, Depends(get_db)]) -> Driver:
    driver = get_driver_by_user_id(db, user.id)
    if not driver:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь водителем")
    return driver


@router.get("/orders", response_model=DeliveryOrderListResponse)
async def driver_orders(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    driver: Annotated[Driver, Depends(get_current_driver)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[DeliveryOrderStatus] = None,
):
    """Заказы, назначенные на текущего водителя."""
    items, total = get_orders_for_driver(db, driver.id, skip=skip, limit=limit, status=status)
    out_items = []
    for o in items:
        try:
            out_items.append(DeliveryOrderResponse.model_validate(o))
        except Exception:
            # Пропускаем некорректные записи (с NULL в обязательных полях)
            continue
    return DeliveryOrderListResponse(items=out_items, total=total, skip=skip, limit=limit)


@router.get("/orders/{order_id}", response_model=DeliveryOrderResponse)
async def driver_get_order(
    order_id: int,
    driver: Annotated[Driver, Depends(get_current_driver)],
    db: Annotated[Session, Depends(get_db)],
):
    """Заказ по ID (только назначенный на водителя)."""
    order = get_delivery_order_by_id(db, order_id)
    if not order or order.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return DeliveryOrderResponse.model_validate(order)


@router.post("/orders/{order_id}/accept", response_model=DeliveryOrderResponse)
async def accept_order(
    order_id: int,
    driver: Annotated[Driver, Depends(get_current_driver)],
    db: Annotated[Session, Depends(get_db)],
):
    """ТЗ п.6.3 — принять заказ (оставить назначение)."""
    order = get_delivery_order_by_id(db, order_id)
    if not order or order.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    if order.status != DeliveryOrderStatus.DRIVER_ASSIGNED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Заказ уже принят или отменён")
    return DeliveryOrderResponse.model_validate(order)


@router.post("/orders/{order_id}/reject", response_model=DeliveryOrderResponse)
async def reject_order(
    order_id: int,
    driver: Annotated[Driver, Depends(get_current_driver)],
    db: Annotated[Session, Depends(get_db)],
):
    """ТЗ п.6.3 — отклонить заказ. Заказ возвращается в статус created для повторного назначения администратором."""
    order = get_delivery_order_by_id(db, order_id)
    if not order or order.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    if order.status != DeliveryOrderStatus.DRIVER_ASSIGNED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Заказ уже принят или отменён")
    unassign_driver(db, order_id)
    order = get_delivery_order_by_id(db, order_id)
    return DeliveryOrderResponse.model_validate(order)


ALLOWED_DRIVER_STATUS_TRANSITIONS = {
    DeliveryOrderStatus.DRIVER_ASSIGNED: [DeliveryOrderStatus.DRIVER_ON_WAY],
    DeliveryOrderStatus.DRIVER_ON_WAY: [DeliveryOrderStatus.PICKED_UP],
    DeliveryOrderStatus.PICKED_UP: [DeliveryOrderStatus.IN_DELIVERY],
    DeliveryOrderStatus.IN_DELIVERY: [DeliveryOrderStatus.DELIVERED],
    DeliveryOrderStatus.DELIVERED: [DeliveryOrderStatus.COMPLETED],
}


@router.patch("/orders/{order_id}/status", response_model=DeliveryOrderResponse)
async def driver_update_status(
    order_id: int,
    body: DeliveryOrderStatusUpdate,
    driver: Annotated[Driver, Depends(get_current_driver)],
    db: Annotated[Session, Depends(get_db)],
):
    """ТЗ п.7 — смена статуса водителем: driver_on_way, picked_up, in_delivery, delivered, completed."""
    order = get_delivery_order_by_id(db, order_id)
    if not order or order.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    allowed = ALLOWED_DRIVER_STATUS_TRANSITIONS.get(order.status, [])
    if body.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Нельзя перевести заказ из {order.status} в {body.status}",
        )
    if body.status == DeliveryOrderStatus.COMPLETED and order.status != DeliveryOrderStatus.DELIVERED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Сначала установите статус delivered")
    update_order_status(db, order_id, body.status, "driver")
    if body.status == DeliveryOrderStatus.DELIVERED:
        update_order_status(db, order_id, DeliveryOrderStatus.COMPLETED, "driver")
    order = get_delivery_order_by_id(db, order_id)
    return DeliveryOrderResponse.model_validate(order)
