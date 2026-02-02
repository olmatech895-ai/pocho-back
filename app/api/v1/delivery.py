"""
API доставки по ТЗ: расчёт цены, заказы, баланс (пользователь).
"""
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.delivery import DeliveryOrderStatus
from app.schemas.delivery import (
    PointSchema,
    PriceCalculationRequest,
    PriceCalculationResponse,
    DeliveryOrderCreate,
    DeliveryOrderResponse,
    DeliveryOrderListResponse,
    OrderCancelRequest,
    UserBalanceResponse,
    UserBalanceLogResponse,
)
from app.services.delivery_service.crud import (
    calculate_delivery_cost,
    create_delivery_order,
    get_delivery_order_by_id,
    get_user_orders,
    cancel_order,
    get_user_balance,
)
from app.models.delivery import UserBalanceLog

router = APIRouter(prefix="/delivery", tags=["Доставка"])


@router.post("/calculate-price", response_model=PriceCalculationResponse)
async def calculate_price(
    body: PriceCalculationRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """ТЗ п.2.4 — расчёт стоимости доставки между двумя точками."""
    try:
        distance_km, cost, tariff = calculate_delivery_cost(db, body.pickup, body.dropoff)
        if not tariff:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Нет активного тарифа доставки. Обратитесь к администратору."
            )
        if distance_km < 0 or cost < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка расчёта: некорректные координаты или параметры тарифа"
            )
        return PriceCalculationResponse(
            distance_km=round(distance_km, 2),
            delivery_cost=round(cost, 2),
            min_total=tariff.min_total,
            cost_per_km=tariff.cost_per_km,
            base_fixed=tariff.base_fixed,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при расчёте стоимости: {str(e)}"
        )


@router.post("/orders", response_model=DeliveryOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: DeliveryOrderCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """ТЗ п.4 — создание заказа (проверка баланса, списание, поиск водителя)."""
    try:
        order = create_delivery_order(db, current_user.id, body)
        out = DeliveryOrderResponse.model_validate(order)
        if order.driver:
            out.driver_name = order.driver.full_name
            out.driver_phone = order.driver.phone_number
        return out
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/orders", response_model=DeliveryOrderListResponse)
async def my_orders(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[DeliveryOrderStatus] = None,
):
    """Список заказов текущего пользователя."""
    items, total = get_user_orders(db, current_user.id, skip=skip, limit=limit, status=status)
    out_items = []
    for o in items:
        try:
            r = DeliveryOrderResponse.model_validate(o)
            if o.driver:
                r.driver_name = o.driver.full_name
                r.driver_phone = o.driver.phone_number
            out_items.append(r)
        except Exception:
            # Пропускаем некорректные записи (с NULL в обязательных полях)
            continue
    return DeliveryOrderListResponse(items=out_items, total=total, skip=skip, limit=limit)


@router.get("/orders/{order_id}", response_model=DeliveryOrderResponse)
async def get_order(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Заказ по ID (только свой)."""
    order = get_delivery_order_by_id(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    out = DeliveryOrderResponse.model_validate(order)
    if order.driver:
        out.driver_name = order.driver.full_name
        out.driver_phone = order.driver.phone_number
    return out


@router.post("/orders/{order_id}/cancel", response_model=DeliveryOrderResponse)
async def cancel_my_order(
    order_id: int,
    body: Optional[OrderCancelRequest] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """ТЗ п.8 — отмена заказа пользователем (до получения посылки водителем)."""
    order = get_delivery_order_by_id(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    if order.status == DeliveryOrderStatus.CANCELED:
        return DeliveryOrderResponse.model_validate(order)
    if order.status in (DeliveryOrderStatus.PICKED_UP, DeliveryOrderStatus.IN_DELIVERY, DeliveryOrderStatus.DELIVERED, DeliveryOrderStatus.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отменить заказ после получения посылки водителем",
        )
    reason = body.reason if body else None
    order = cancel_order(db, order_id, current_user.id, reason=reason, refund=True)
    return DeliveryOrderResponse.model_validate(order)


@router.get("/balance", response_model=UserBalanceResponse)
async def my_balance(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """ТЗ п.5 — баланс пользователя."""
    balance = get_user_balance(db, current_user.id)
    return UserBalanceResponse(balance=balance)


@router.get("/balance/log", response_model=List[UserBalanceLogResponse])
async def balance_log(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """История движений по балансу."""
    rows = db.query(UserBalanceLog).filter(UserBalanceLog.user_id == current_user.id).order_by(UserBalanceLog.created_at.desc()).offset(skip).limit(limit).all()
    return [UserBalanceLogResponse.model_validate(r) for r in rows]
