"""
Модели для глобального чата
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class MessageType(str, enum.Enum):
    """Типы сообщений в глобальном чате"""
    TEXT = "text"  # Текстовое сообщение
    IMAGE = "image"  # Изображение
    VIDEO = "video"  # Видео
    FILE = "file"  # Файл
    AUDIO = "audio"  # Аудио


class GlobalChatMessage(Base):
    """
    Сообщение в глобальном чате
    
    Все пользователи видят все сообщения (кроме заблокированных)
    """
    __tablename__ = "global_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Тип сообщения
    message_type = Column(
        SQLEnum(MessageType),
        default=MessageType.TEXT,
        nullable=False,
        index=True
    )
    
    # Текст сообщения (может быть пустым для медиа-файлов)
    message = Column(Text, nullable=True)
    
    # Прикрепленные файлы (JSON массив URL файлов)
    attachments = Column(JSON, nullable=True)  # [{"url": "...", "type": "image", "name": "photo.jpg", "size": 12345}]
    
    # Метаданные сообщения (JSON для дополнительной информации)
    # Используем extra_metadata вместо metadata, т.к. metadata - зарезервированное имя в SQLAlchemy
    extra_metadata = Column(JSON, nullable=True)  # {"duration": 120, "thumbnail": "...", etc.}
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Мягкое удаление (для всех)
    
    # Связи
    user = relationship("User", backref="global_chat_messages")
    hidden_for_users = relationship("HiddenGlobalChatMessage", back_populates="message", cascade="all, delete-orphan")


class UserBlock(Base):
    """
    Блокировка пользователей
    
    Если пользователь A заблокировал пользователя B, то A не будет видеть сообщения от B
    """
    __tablename__ = "user_blocks"

    id = Column(Integer, primary_key=True, index=True)
    blocker_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Кто блокирует
    blocked_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Кого блокируют
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Уникальность: один пользователь не может заблокировать другого дважды
    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='uq_user_block'),
    )
    
    # Связи
    blocker = relationship("User", foreign_keys=[blocker_id], backref="blocked_users")
    blocked = relationship("User", foreign_keys=[blocked_id], backref="blocked_by_users")


class HiddenGlobalChatMessage(Base):
    """
    Скрытые сообщения для конкретного пользователя
    
    Используется для удаления истории чата только у конкретного пользователя
    """
    __tablename__ = "hidden_global_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("global_chat_messages.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Временные метки
    hidden_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Уникальность: одно сообщение может быть скрыто для пользователя только один раз
    __table_args__ = (
        UniqueConstraint('message_id', 'user_id', name='uq_hidden_message_user'),
    )
    
    # Связи
    message = relationship("GlobalChatMessage", back_populates="hidden_for_users")
    user = relationship("User", backref="hidden_global_chat_messages")

