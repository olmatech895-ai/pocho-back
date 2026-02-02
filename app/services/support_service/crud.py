"""
CRUD операции для Support Service
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func as sql_func
from datetime import datetime, timezone

from app.models.support import SupportTicket, SupportMessage, TicketStatus, TicketPriority
from app.schemas.support import (
    SupportTicketCreate,
    SupportTicketUpdate,
    SupportMessageCreate,
)


def create_ticket(
    db: Session,
    user_id: int,
    ticket_data: SupportTicketCreate
) -> SupportTicket:
    """Создание нового тикета с первым сообщением"""
    # Создаем тикет
    ticket = SupportTicket(
        user_id=user_id,
        subject=ticket_data.subject,
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        is_read_by_user=True,
        is_read_by_admin=False
    )
    db.add(ticket)
    db.flush()  # Получаем ID тикета
    
    # Создаем первое сообщение
    first_message = SupportMessage(
        ticket_id=ticket.id,
        user_id=user_id,
        message=ticket_data.message,
        is_from_user=True
    )
    db.add(first_message)
    
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_by_id(db: Session, ticket_id: int) -> Optional[SupportTicket]:
    """Получение тикета по ID"""
    return db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()


def get_user_tickets(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[TicketStatus] = None
) -> Tuple[List[SupportTicket], int]:
    """Получение тикетов пользователя"""
    query = db.query(SupportTicket).filter(SupportTicket.user_id == user_id)
    
    if status:
        query = query.filter(SupportTicket.status == status)
    
    total = query.count()
    tickets = query.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit).all()
    
    return tickets, total


def get_all_tickets(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[TicketStatus] = None,
    assigned_to: Optional[int] = None,
    user_id: Optional[int] = None
) -> Tuple[List[SupportTicket], int]:
    """Получение всех тикетов (для администратора)"""
    query = db.query(SupportTicket)
    
    if status:
        query = query.filter(SupportTicket.status == status)
    
    if assigned_to is not None:
        if assigned_to == 0:
            # Не назначенные никому
            query = query.filter(SupportTicket.assigned_to.is_(None))
        else:
            query = query.filter(SupportTicket.assigned_to == assigned_to)
    
    if user_id:
        query = query.filter(SupportTicket.user_id == user_id)
    
    total = query.count()
    tickets = query.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit).all()
    
    return tickets, total


def update_ticket(
    db: Session,
    ticket_id: int,
    ticket_update: SupportTicketUpdate
) -> Optional[SupportTicket]:
    """Обновление тикета"""
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
    
    update_data = ticket_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "status":
            ticket.status = value
            if value == TicketStatus.RESOLVED and not ticket.resolved_at:
                ticket.resolved_at = datetime.now(timezone.utc)
            elif value == TicketStatus.CLOSED and not ticket.closed_at:
                ticket.closed_at = datetime.now(timezone.utc)
        else:
            setattr(ticket, field, value)
    
    db.commit()
    db.refresh(ticket)
    return ticket


def add_message(
    db: Session,
    ticket_id: int,
    user_id: int,
    message_data: SupportMessageCreate,
    is_from_user: bool
) -> Optional[SupportMessage]:
    """Добавление сообщения в тикет"""
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
    
    # Проверка доступа
    if is_from_user and ticket.user_id != user_id:
        return None
    
    # Если пользователь отправил сообщение, помечаем как непрочитанное для админа
    if is_from_user:
        ticket.is_read_by_admin = False
        ticket.is_read_by_user = True
        # Если тикет был закрыт/решен, открываем его заново
        if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            ticket.status = TicketStatus.OPEN
    else:
        # Если админ отправил сообщение, помечаем как непрочитанное для пользователя
        ticket.is_read_by_user = False
        ticket.is_read_by_admin = True
        # Если тикет был открыт, переводим в "в работе"
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
    
    # Создаем сообщение
    import json
    attachments_json = None
    if message_data.attachments:
        attachments_json = json.dumps(message_data.attachments)
    
    message = SupportMessage(
        ticket_id=ticket_id,
        user_id=user_id,
        message=message_data.message,
        is_from_user=is_from_user,
        attachments=attachments_json
    )
    db.add(message)
    
    db.commit()
    db.refresh(message)
    return message


def get_ticket_messages(
    db: Session,
    ticket_id: int,
    user_id: int,
    is_admin: bool = False
) -> List[SupportMessage]:
    """Получение сообщений тикета"""
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        return []
    
    # Проверка доступа
    if not is_admin and ticket.user_id != user_id:
        return []
    
    return db.query(SupportMessage).filter(
        SupportMessage.ticket_id == ticket_id
    ).order_by(SupportMessage.created_at.asc()).all()


def mark_ticket_as_read(
    db: Session,
    ticket_id: int,
    user_id: int,
    is_admin: bool = False
) -> Optional[SupportTicket]:
    """Отметить тикет как прочитанный"""
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
    
    # Проверка доступа
    if not is_admin and ticket.user_id != user_id:
        return None
    
    if is_admin:
        ticket.is_read_by_admin = True
    else:
        ticket.is_read_by_user = True
    
    db.commit()
    db.refresh(ticket)
    return ticket


def get_unread_tickets_count(db: Session, user_id: int, is_admin: bool = False) -> int:
    """Получение количества непрочитанных тикетов"""
    if is_admin:
        return db.query(SupportTicket).filter(
            SupportTicket.is_read_by_admin == False
        ).count()
    else:
        return db.query(SupportTicket).filter(
            and_(
                SupportTicket.user_id == user_id,
                SupportTicket.is_read_by_user == False
            )
        ).count()


def get_ticket_stats(db: Session) -> dict:
    """Получение статистики тикетов (для администратора)"""
    total = db.query(SupportTicket).count()
    open_count = db.query(SupportTicket).filter(SupportTicket.status == TicketStatus.OPEN).count()
    in_progress_count = db.query(SupportTicket).filter(SupportTicket.status == TicketStatus.IN_PROGRESS).count()
    resolved_count = db.query(SupportTicket).filter(SupportTicket.status == TicketStatus.RESOLVED).count()
    closed_count = db.query(SupportTicket).filter(SupportTicket.status == TicketStatus.CLOSED).count()
    
    return {
        "total": total,
        "open": open_count,
        "in_progress": in_progress_count,
        "resolved": resolved_count,
        "closed": closed_count
    }

