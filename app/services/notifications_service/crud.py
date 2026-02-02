"""
CRUD операции для Notifications Service
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user_extended import UserNotification
from app.schemas.user_extended import UserNotificationUpdate


def get_notifications_by_user_id(db: Session, user_id: int) -> Optional[UserNotification]:
    """Получение настроек уведомлений пользователя"""
    return db.query(UserNotification).filter(UserNotification.user_id == user_id).first()


def create_notifications(db: Session, user_id: int) -> UserNotification:
    """Создание настроек уведомлений"""
    db_notifications = UserNotification(
        user_id=user_id,
        enabled=True,
        price_alerts=True,
        new_stations=True,
        promotions=True,
        reviews=True
    )
    db.add(db_notifications)
    db.commit()
    db.refresh(db_notifications)
    return db_notifications


def update_notifications(
    db: Session,
    user_id: int,
    notifications_update: UserNotificationUpdate
) -> Optional[UserNotification]:
    """Обновление настроек уведомлений"""
    notifications = get_notifications_by_user_id(db, user_id)
    if not notifications:
        return None
    
    update_data = notifications_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(notifications, field, value)
    
    db.commit()
    db.refresh(notifications)
    return notifications

