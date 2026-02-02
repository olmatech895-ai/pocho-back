"""
API доставки для администратора: тарифы, заказы, отмена (ТЗ п.3, п.8).
"""
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.delivery import DeliveryOrderStatus
from app.schemas.delivery import (
    DeliveryTariffCreate,
    DeliveryTariffUpdate,
    DeliveryTariffResponse,
    DeliveryOrderResponse,
    DeliveryOrderListResponse,
    OrderCancelRequest,
    AssignDriverRequest,
)
from app.services.delivery_service.tariff_crud import (
    create_tariff,
    get_tariff_by_id,
    get_tariffs,
    update_tariff,
    delete_tariff,
)
from app.services.delivery_service.crud import (
    get_delivery_order_by_id,
    get_user_orders,
    cancel_order,
    assign_driver_by_admin,
)
from app.models.delivery import DeliveryOrder

router = APIRouter(prefix="/admin/delivery", tags=["Админ: Доставка"])


# --- Тарифы (ТЗ п.3) ---
@router.post("/tariffs", response_model=DeliveryTariffResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_tariff(
    body: DeliveryTariffCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Создание тарифа доставки."""
    return create_tariff(db, body)


@router.get("/tariffs", response_model=List[DeliveryTariffResponse])
async def admin_list_tariffs(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = None,
):
    """Список тарифов."""
    return get_tariffs(db, skip=skip, limit=limit, is_active=is_active)


@router.get("/tariffs/{tariff_id}", response_model=DeliveryTariffResponse)
async def admin_get_tariff(
    tariff_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Тариф по ID."""
    t = get_tariff_by_id(db, tariff_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тариф не найден")
    return t


@router.put("/tariffs/{tariff_id}", response_model=DeliveryTariffResponse)
async def admin_update_tariff(
    tariff_id: int,
    body: DeliveryTariffUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Обновление тарифа."""
    t = update_tariff(db, tariff_id, body)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тариф не найден")
    return t


@router.delete("/tariffs/{tariff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_tariff(
    tariff_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Удаление тарифа."""
    if not delete_tariff(db, tariff_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тариф не найден")


# --- Заказы ---
@router.get("/orders", response_model=DeliveryOrderListResponse)
async def admin_list_orders(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    status: Optional[DeliveryOrderStatus] = None,
    user_id: Optional[int] = None,
):
    """Список всех заказов доставки."""
    q = db.query(DeliveryOrder)
    # Фильтруем некорректные записи с NULL в обязательных полях
    q = q.filter(
        DeliveryOrder.user_id.isnot(None),
        DeliveryOrder.dropoff_latitude.isnot(None),
        DeliveryOrder.dropoff_longitude.isnot(None),
        DeliveryOrder.delivery_cost.isnot(None)
    )
    if status is not None:
        q = q.filter(DeliveryOrder.status == status)
    if user_id is not None:
        q = q.filter(DeliveryOrder.user_id == user_id)
    total = q.count()
    items = q.order_by(DeliveryOrder.created_at.desc()).offset(skip).limit(limit).all()
    out = []
    for o in items:
        try:
            out.append(DeliveryOrderResponse.model_validate(o))
        except Exception:
            # Пропускаем некорректные записи (с NULL в обязательных полях)
            continue
    return DeliveryOrderListResponse(items=out, total=total, skip=skip, limit=limit)


@router.post("/orders/{order_id}/assign-driver", response_model=DeliveryOrderResponse)
async def admin_assign_driver(
    order_id: int,
    body: AssignDriverRequest,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Назначение водителя на заказ. Заказ должен быть в статусе created (ожидает назначения)."""
    try:
        order = assign_driver_by_admin(db, order_id, body.driver_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    r = DeliveryOrderResponse.model_validate(order)
    if order.driver:
        r.driver_name = order.driver.full_name
        r.driver_phone = order.driver.phone_number
    return r


@router.get("/orders/{order_id}", response_model=DeliveryOrderResponse)
async def admin_get_order(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Заказ по ID."""
    order = get_delivery_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    r = DeliveryOrderResponse.model_validate(order)
    if order.driver:
        r.driver_name = order.driver.full_name
        r.driver_phone = order.driver.phone_number
    return r


@router.post("/orders/{order_id}/cancel", response_model=DeliveryOrderResponse)
async def admin_cancel_order(
    order_id: int,
    body: Optional[OrderCancelRequest] = None,
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """ТЗ п.8 — отмена заказа администратором на любом этапе."""
    order = get_delivery_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    if order.status == DeliveryOrderStatus.CANCELED:
        return DeliveryOrderResponse.model_validate(order)
    reason = (body.reason if body else None) or "Отмена администратором"
    order = cancel_order(db, order_id, current_user.id, reason=reason, refund=True, source="admin")
    return DeliveryOrderResponse.model_validate(order)
