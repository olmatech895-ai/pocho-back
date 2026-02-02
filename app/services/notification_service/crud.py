"""
CRUD операции для Notification Service
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, not_
from datetime import datetime, timezone

from app.models.notification import Notification, NotificationReadStatus
from app.schemas.notification import NotificationCreate, NotificationUpdate


def create_notification(
    db: Session,
    notification: NotificationCreate
) -> Notification:
    """Создание уведомления"""
    db_notification = Notification(
        user_id=notification.user_id,
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        extra_data=notification.extra_data,
        is_read=False
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_notification_by_id(db: Session, notification_id: int) -> Optional[Notification]:
    """Получение уведомления по ID"""
    return db.query(Notification).filter(Notification.id == notification_id).first()


def get_user_notifications(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    unread_only: Optional[bool] = None
) -> Tuple[List[Notification], int]:
    """
    Получение уведомлений пользователя
    
    Включает:
    - Персональные уведомления (user_id = user_id), которые не удалены
    - Глобальные уведомления (user_id = None), которые не скрыты пользователем
    
    Исключает:
    - Удаленные персональные уведомления
    - Скрытые глобальные уведомления (через NotificationReadStatus.is_deleted)
    """
    from sqlalchemy import exists
    
    # Базовый запрос: персональные + глобальные уведомления
    # Исключаем скрытые глобальные уведомления
    query = db.query(Notification).filter(
        or_(
            Notification.user_id == user_id,  # Персональные
            and_(
                Notification.user_id.is_(None),  # Глобальные
                ~exists().where(
                    and_(
                        NotificationReadStatus.notification_id == Notification.id,
                        NotificationReadStatus.user_id == user_id,
                        NotificationReadStatus.is_deleted == True
                    )
                )
            )
        )
    )
    
    # Фильтр по статусу прочтения
    if unread_only is not None:
        if unread_only:
            # Непрочитанные: персональные с is_read=False 
            # или глобальные без записи в NotificationReadStatus с is_read=True
            query = query.filter(
                or_(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False
                    ),
                    and_(
                        Notification.user_id.is_(None),
                        ~exists().where(
                            and_(
                                NotificationReadStatus.notification_id == Notification.id,
                                NotificationReadStatus.user_id == user_id,
                                NotificationReadStatus.is_read == True
                            )
                        )
                    )
                )
            )
        else:
            # Прочитанные: персональные с is_read=True 
            # или глобальные с is_read=True в NotificationReadStatus
            query = query.filter(
                or_(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == True
                    ),
                    and_(
                        Notification.user_id.is_(None),
                        exists().where(
                            and_(
                                NotificationReadStatus.notification_id == Notification.id,
                                NotificationReadStatus.user_id == user_id,
                                NotificationReadStatus.is_read == True
                            )
                        )
                    )
                )
            )
    
    # Получаем общее количество
    total = query.count()
    
    # Применяем пагинацию и сортировку
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    return notifications, total


def get_unread_count(db: Session, user_id: int) -> int:
    """Получение количества непрочитанных уведомлений"""
    from sqlalchemy import exists
    
    # Непрочитанные: персональные с is_read=False 
    # или глобальные без записи в NotificationReadStatus с is_read=True и не скрытые
    return db.query(Notification).filter(
        or_(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            ),
            and_(
                Notification.user_id.is_(None),
                # Не скрыто
                ~exists().where(
                    and_(
                        NotificationReadStatus.notification_id == Notification.id,
                        NotificationReadStatus.user_id == user_id,
                        NotificationReadStatus.is_deleted == True
                    )
                ),
                # Не прочитано
                ~exists().where(
                    and_(
                        NotificationReadStatus.notification_id == Notification.id,
                        NotificationReadStatus.user_id == user_id,
                        NotificationReadStatus.is_read == True
                    )
                )
            )
        )
    ).count()


def mark_notification_as_read(
    db: Session,
    notification_id: int,
    user_id: int
) -> Optional[Notification]:
    """
    Отметить уведомление как прочитанное
    
    - Персональные уведомления: обновляем is_read в Notification
    - Глобальные уведомления: создаем/обновляем запись в NotificationReadStatus
    """
    notification = get_notification_by_id(db, notification_id)
    
    if not notification:
        return None
    
    # Персональное уведомление
    if notification.user_id is not None:
        # Проверяем, что уведомление принадлежит пользователю
        if notification.user_id != user_id:
            return None
        
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
        return notification
    
    # Глобальное уведомление - создаем/обновляем запись в NotificationReadStatus
    read_status = db.query(NotificationReadStatus).filter(
        and_(
            NotificationReadStatus.notification_id == notification_id,
            NotificationReadStatus.user_id == user_id
        )
    ).first()
    
    if read_status:
        # Обновляем существующую запись
        read_status.is_read = True
        read_status.read_at = datetime.now(timezone.utc)
    else:
        # Создаем новую запись
        read_status = NotificationReadStatus(
            notification_id=notification_id,
            user_id=user_id,
            is_read=True,
            read_at=datetime.now(timezone.utc),
            is_deleted=False
        )
        db.add(read_status)
    
    db.commit()
    return notification


def mark_all_as_read(db: Session, user_id: int) -> int:
    """
    Отметить все уведомления пользователя как прочитанные
    
    - Персональные уведомления: обновляем is_read в Notification
    - Глобальные уведомления: создаем/обновляем записи в NotificationReadStatus
    """
    count = 0
    now = datetime.now(timezone.utc)
    
    # Обновляем персональные уведомления
    personal_updated = db.query(Notification).filter(
        and_(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
    ).update({
        Notification.is_read: True,
        Notification.read_at: now
    })
    count += personal_updated
    
    # Получаем все глобальные уведомления
    global_notifications = db.query(Notification.id).filter(
        Notification.user_id.is_(None)
    ).all()
    
    # Для каждого глобального уведомления создаем/обновляем запись
    for (notification_id,) in global_notifications:
        read_status = db.query(NotificationReadStatus).filter(
            and_(
                NotificationReadStatus.notification_id == notification_id,
                NotificationReadStatus.user_id == user_id
            )
        ).first()
        
        if read_status:
            if not read_status.is_read:
                read_status.is_read = True
                read_status.read_at = now
                count += 1
        else:
            read_status = NotificationReadStatus(
                notification_id=notification_id,
                user_id=user_id,
                is_read=True,
                read_at=now,
                is_deleted=False
            )
            db.add(read_status)
            count += 1
    
    db.commit()
    return count


def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
    """
    Удаление уведомления для пользователя
    
    - Персональные уведомления: полностью удаляются из БД
    - Глобальные уведомления: помечаются как удаленные через NotificationReadStatus
    """
    notification = get_notification_by_id(db, notification_id)
    
    if not notification:
        return False
    
    # Персональное уведомление - удаляем полностью
    if notification.user_id is not None:
        # Проверяем, что уведомление принадлежит пользователю
        if notification.user_id != user_id:
            return False
        
        db.delete(notification)
        db.commit()
        return True
    
    # Глобальное уведомление - создаем/обновляем запись в NotificationReadStatus с is_deleted=True
    read_status = db.query(NotificationReadStatus).filter(
        and_(
            NotificationReadStatus.notification_id == notification_id,
            NotificationReadStatus.user_id == user_id
        )
    ).first()
    
    if read_status:
        # Обновляем существующую запись
        read_status.is_deleted = True
        read_status.deleted_at = datetime.now(timezone.utc)
    else:
        # Создаем новую запись
        read_status = NotificationReadStatus(
            notification_id=notification_id,
            user_id=user_id,
            is_read=False,
            is_deleted=True,
            deleted_at=datetime.now(timezone.utc)
        )
        db.add(read_status)
    
    db.commit()
    return True


def delete_all_user_notifications(db: Session, user_id: int) -> int:
    """
    Удаление всех уведомлений пользователя
    
    Возвращает количество удаленных уведомлений
    """
    count = 0
    
    # Удаляем все персональные уведомления
    personal_deleted = db.query(Notification).filter(
        Notification.user_id == user_id
    ).delete()
    count += personal_deleted
    
    # Помечаем все глобальные уведомления как удаленные
    # Получаем все глобальные уведомления
    global_notifications = db.query(Notification.id).filter(
        Notification.user_id.is_(None)
    ).all()
    
    global_ids = [n[0] for n in global_notifications]
    
    # Для каждого глобального уведомления создаем/обновляем запись с is_deleted=True
    for notification_id in global_ids:
        read_status = db.query(NotificationReadStatus).filter(
            and_(
                NotificationReadStatus.notification_id == notification_id,
                NotificationReadStatus.user_id == user_id
            )
        ).first()
        
        if read_status:
            if not read_status.is_deleted:
                read_status.is_deleted = True
                read_status.deleted_at = datetime.now(timezone.utc)
                count += 1
        else:
            read_status = NotificationReadStatus(
                notification_id=notification_id,
                user_id=user_id,
                is_read=False,
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc)
            )
            db.add(read_status)
            count += 1
    
    db.commit()
    return count


def delete_notification_admin(db: Session, notification_id: int) -> bool:
    """
    Удаление уведомления администратором (любого типа)
    
    Удаляет уведомление полностью из БД, включая все связанные записи
    """
    notification = get_notification_by_id(db, notification_id)
    
    if not notification:
        return False
    
    # Удаляем все связанные записи статусов прочтения
    db.query(NotificationReadStatus).filter(
        NotificationReadStatus.notification_id == notification_id
    ).delete()
    
    # Удаляем само уведомление
    db.delete(notification)
    db.commit()
    return True


def get_all_notifications(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    notification_type: Optional[str] = None
) -> Tuple[List[Notification], int]:
    """Получение всех уведомлений (для администратора)"""
    query = db.query(Notification)
    
    if user_id is not None:
        query = query.filter(Notification.user_id == user_id)
    
    if notification_type is not None:
        query = query.filter(Notification.notification_type == notification_type)
    
    total = query.count()
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    return notifications, total


