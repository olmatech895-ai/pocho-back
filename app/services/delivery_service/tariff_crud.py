"""CRUD тарифов доставки (админ)."""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.delivery import DeliveryTariff
from app.schemas.delivery import DeliveryTariffCreate, DeliveryTariffUpdate


def create_tariff(db: Session, data: DeliveryTariffCreate) -> DeliveryTariff:
    t = DeliveryTariff(
        name=data.name,
        cost_per_km=data.cost_per_km,
        min_total=data.min_total,
        base_fixed=data.base_fixed,
        extra_coefficients=data.extra_coefficients,
        is_active=data.is_active,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def get_tariff_by_id(db: Session, tariff_id: int) -> Optional[DeliveryTariff]:
    return db.query(DeliveryTariff).filter(DeliveryTariff.id == tariff_id).first()


def get_tariffs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> List[DeliveryTariff]:
    q = db.query(DeliveryTariff)
    if is_active is not None:
        q = q.filter(DeliveryTariff.is_active == is_active)
    return q.order_by(DeliveryTariff.id).offset(skip).limit(limit).all()


def update_tariff(db: Session, tariff_id: int, data: DeliveryTariffUpdate) -> Optional[DeliveryTariff]:
    t = get_tariff_by_id(db, tariff_id)
    if not t:
        return None
    upd = data.model_dump(exclude_unset=True)
    for k, v in upd.items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


def delete_tariff(db: Session, tariff_id: int) -> bool:
    t = get_tariff_by_id(db, tariff_id)
    if not t:
        return False
    db.delete(t)
    db.commit()
    return True
