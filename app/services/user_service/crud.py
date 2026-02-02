"""
CRUD операции для User Service
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user_extended import UserExtended
from app.schemas.user_extended import UserExtendedCreate, UserExtendedUpdate


def get_user_extended_by_id(db: Session, user_id: int) -> Optional[UserExtended]:
    """Получение расширенного пользователя по user_id"""
    return db.query(UserExtended).filter(UserExtended.user_id == user_id).first()


def get_user_extended_by_phone(db: Session, phone: str) -> Optional[UserExtended]:
    """Получение расширенного пользователя по телефону"""
    return db.query(UserExtended).filter(UserExtended.phone == phone).first()


def create_user_extended(db: Session, user_extended: UserExtendedCreate) -> UserExtended:
    """Создание расширенного пользователя"""
    db_user = UserExtended(**user_extended.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_extended(
    db: Session,
    user_id: int,
    user_update: UserExtendedUpdate
) -> Optional[UserExtended]:
    """Обновление расширенного пользователя"""
    user = get_user_extended_by_id(db, user_id)
    if not user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user


def update_user_balance(db: Session, user_id: int, amount: float) -> Optional[UserExtended]:
    """Обновление баланса пользователя"""
    user = get_user_extended_by_id(db, user_id)
    if not user:
        return None
    
    user.balance += amount
    db.commit()
    db.refresh(user)
    return user


def increment_stations_visited(db: Session, user_id: int) -> Optional[UserExtended]:
    """Увеличение счетчика посещенных заправок"""
    user = get_user_extended_by_id(db, user_id)
    if not user:
        return None
    
    user.total_stations_visited += 1
    db.commit()
    db.refresh(user)
    return user


def add_to_total_spent(db: Session, user_id: int, amount: float) -> Optional[UserExtended]:
    """Добавление к общей сумме потраченных средств"""
    user = get_user_extended_by_id(db, user_id)
    if not user:
        return None
    
    user.total_spent += amount
    db.commit()
    db.refresh(user)
    return user

