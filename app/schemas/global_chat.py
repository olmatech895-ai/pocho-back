"""
Схемы для глобального чата
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.global_chat import MessageType


class AttachmentInfo(BaseModel):
    """Информация о прикрепленном файле"""
    url: str = Field(..., description="URL файла")
    type: str = Field(..., description="Тип файла: image, video, file, audio")
    name: Optional[str] = Field(None, description="Имя файла")
    size: Optional[int] = Field(None, description="Размер файла в байтах")
    thumbnail: Optional[str] = Field(None, description="URL превью (для видео)")


class GlobalChatMessageBase(BaseModel):
    """Базовая схема сообщения"""
    message: Optional[str] = Field(None, description="Текст сообщения (может быть пустым для медиа)")
    message_type: MessageType = Field(MessageType.TEXT, description="Тип сообщения")
    attachments: Optional[List[AttachmentInfo]] = Field(None, description="Прикрепленные файлы")
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные")


class GlobalChatMessageCreate(GlobalChatMessageBase):
    """Схема создания сообщения"""
    pass


class GlobalChatMessageResponse(GlobalChatMessageBase):
    """Схема ответа сообщения"""
    id: int
    user_id: int
    user_name: Optional[str] = Field(None, description="Имя пользователя")
    user_avatar: Optional[str] = Field(None, description="Аватар пользователя")
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GlobalChatMessageListResponse(BaseModel):
    """Схема списка сообщений"""
    messages: List[GlobalChatMessageResponse]
    total: int
    skip: int
    limit: int
    online_count: int = Field(..., description="Количество пользователей онлайн")


class GlobalChatSearchResponse(BaseModel):
    """Схема результатов поиска"""
    messages: List[GlobalChatMessageResponse]
    total: int
    query: str
    skip: int
    limit: int


class UserBlockCreate(BaseModel):
    """Схема блокировки пользователя"""
    blocked_user_id: int = Field(..., description="ID пользователя для блокировки")


class UserBlockResponse(BaseModel):
    """Схема ответа блокировки"""
    id: int
    blocker_id: int
    blocked_id: int
    blocked_user_name: Optional[str] = Field(None, description="Имя заблокированного пользователя")
    created_at: datetime

    class Config:
        from_attributes = True


class BlockedUsersListResponse(BaseModel):
    """Схема списка заблокированных пользователей"""
    blocked_users: List[UserBlockResponse]
    total: int


class OnlineUsersResponse(BaseModel):
    """Схема количества онлайн пользователей"""
    online_count: int
    timestamp: datetime

