"""
Модели для системы технической поддержки
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class TicketStatus(str, enum.Enum):
    """Статусы тикета поддержки"""
    OPEN = "open"  # Открыт
    IN_PROGRESS = "in_progress"  # В работе
    WAITING_FOR_USER = "waiting_for_user"  # Ожидание ответа пользователя
    RESOLVED = "resolved"  # Решен
    CLOSED = "closed"  # Закрыт


class TicketPriority(str, enum.Enum):
    """Приоритеты тикета"""
    LOW = "low"  # Низкий
    MEDIUM = "medium"  # Средний
    HIGH = "high"  # Высокий
    URGENT = "urgent"  # Срочный


class SupportTicket(Base):
    """
    Тикет технической поддержки
    
    Каждый пользователь может создать тикет, администраторы могут отвечать
    """
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Тема/заголовок тикета
    subject = Column(String, nullable=False)
    
    # Статус тикета
    status = Column(
        SQLEnum(TicketStatus),
        default=TicketStatus.OPEN,
        nullable=False,
        index=True
    )
    
    # Приоритет (устанавливается администратором или автоматически)
    priority = Column(
        SQLEnum(TicketPriority),
        default=TicketPriority.MEDIUM,
        nullable=False,
        index=True
    )
    
    # Назначенный администратор (может быть None)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Метка прочитанности для пользователя
    is_read_by_user = Column(Boolean, default=True, nullable=False)
    
    # Метка прочитанности для администратора
    is_read_by_admin = Column(Boolean, default=False, nullable=False, index=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    user = relationship("User", foreign_keys=[user_id], backref="support_tickets")
    assigned_admin = relationship("User", foreign_keys=[assigned_to], backref="assigned_tickets")
    messages = relationship("SupportMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="SupportMessage.created_at")


class SupportMessage(Base):
    """
    Сообщение в тикете поддержки
    
    Сообщения могут отправлять как пользователи, так и администраторы
    """
    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Текст сообщения
    message = Column(Text, nullable=False)
    
    # От кого сообщение: True - от пользователя, False - от администратора
    is_from_user = Column(Boolean, nullable=False, index=True)
    
    # Прикрепленные файлы (URL, JSON массив)
    attachments = Column(String, nullable=True)  # JSON массив URL файлов
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Связи
    ticket = relationship("SupportTicket", back_populates="messages")
    user = relationship("User", backref="support_messages")












