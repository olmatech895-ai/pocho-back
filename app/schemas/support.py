"""
Схемы для системы технической поддержки
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.support import TicketStatus, TicketPriority


class SupportMessageBase(BaseModel):
    """Базовая схема сообщения"""
    message: str = Field(..., min_length=1, description="Текст сообщения")
    attachments: Optional[List[str]] = Field(None, description="Список URL прикрепленных файлов")


class SupportMessageCreate(SupportMessageBase):
    """Схема создания сообщения"""
    pass


class SupportMessageResponse(SupportMessageBase):
    """Схема ответа сообщения"""
    id: int
    ticket_id: int
    user_id: int
    is_from_user: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SupportTicketBase(BaseModel):
    """Базовая схема тикета"""
    subject: str = Field(..., min_length=1, max_length=200, description="Тема тикета")


class SupportTicketCreate(SupportTicketBase):
    """Схема создания тикета (первое сообщение)"""
    message: str = Field(..., min_length=1, description="Первое сообщение в тикете")


class SupportTicketUpdate(BaseModel):
    """Схема обновления тикета"""
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[int] = Field(None, description="ID администратора для назначения")


class SupportTicketResponse(SupportTicketBase):
    """Схема ответа тикета"""
    id: int
    user_id: int
    status: TicketStatus
    priority: TicketPriority
    assigned_to: Optional[int] = None
    is_read_by_user: bool
    is_read_by_admin: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    unread_messages_count: Optional[int] = Field(None, description="Количество непрочитанных сообщений")

    class Config:
        from_attributes = True


class SupportTicketWithMessagesResponse(SupportTicketResponse):
    """Схема тикета с сообщениями"""
    messages: List[SupportMessageResponse] = []


class SupportTicketListResponse(BaseModel):
    """Схема списка тикетов"""
    tickets: List[SupportTicketResponse]
    total: int
    skip: int
    limit: int


class SupportTicketStatsResponse(BaseModel):
    """Схема статистики тикетов"""
    total: int
    open: int
    in_progress: int
    resolved: int
    closed: int












