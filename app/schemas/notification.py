"""
Схемы для уведомлений
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


class NotificationBase(BaseModel):
    """Базовая схема уведомления"""
    title: str = Field(..., min_length=1, max_length=200, description="Заголовок уведомления")
    message: str = Field(..., min_length=1, description="Текст уведомления")
    notification_type: str = Field(default="info", description="Тип уведомления: info, warning, success, error, promotion")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Дополнительные данные (action_url, image_url, etc.)")


class NotificationCreate(NotificationBase):
    """Схема создания уведомления"""
    user_id: Optional[int] = Field(None, description="ID пользователя (None для глобального уведомления)")


class NotificationUpdate(BaseModel):
    """Схема обновления уведомления"""
    is_read: Optional[bool] = Field(None, description="Статус прочтения")


class NotificationResponse(NotificationBase):
    """Схема ответа уведомления"""
    id: int
    user_id: Optional[int] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Схема списка уведомлений"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    skip: int
    limit: int


class NotificationStatsResponse(BaseModel):
    """Схема статистики уведомлений"""
    total: int
    unread: int
    read: int













