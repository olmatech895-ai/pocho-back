"""
Модель уведомлений для пользователей
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Notification(Base):
    """
    Уведомления пользователей
    
    Поддерживает два типа:
    - Персональные уведомления (user_id указан)
    - Глобальные уведомления для всех пользователей (user_id = None)
    
    Для глобальных уведомлений статус прочтения хранится в NotificationReadStatus
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    
    # user_id = None означает глобальное уведомление для всех пользователей
    # user_id указан - персональное уведомление для конкретного пользователя
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Заголовок уведомления
    title = Column(String, nullable=False)
    
    # Текст уведомления
    message = Column(Text, nullable=False)
    
    # Тип уведомления (info, warning, success, error, promotion, etc.)
    notification_type = Column(String, default="info", nullable=False, index=True)
    
    # Статус прочтения (только для персональных уведомлений)
    # Для глобальных уведомлений используется NotificationReadStatus
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    
    # Дата прочтения (только для персональных уведомлений)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Дополнительные данные (JSON для гибкости)
    # Может содержать: action_url, image_url, buttons, etc.
    extra_data = Column(JSON, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Связи
    user = relationship("User", backref="notifications")
    read_statuses = relationship("NotificationReadStatus", back_populates="notification", cascade="all, delete-orphan")


class NotificationReadStatus(Base):
    """
    Статус прочтения глобальных уведомлений для каждого пользователя
    
    Используется для отслеживания:
    - Какие пользователи прочитали глобальное уведомление (is_read)
    - Какие пользователи удалили (скрыли) глобальное уведомление (is_deleted)
    """
    __tablename__ = "notification_read_status"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)  # Флаг удаления/скрытия для пользователя
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Уникальность: один статус на пользователя для каждого уведомления
    __table_args__ = (
        UniqueConstraint('notification_id', 'user_id', name='uq_notification_user_read'),
    )
    
    # Связи
    notification = relationship("Notification", back_populates="read_statuses")
    user = relationship("User", backref="notification_read_statuses")

