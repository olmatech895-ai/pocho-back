"""
CRUD операции для Global Chat Service
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func as sql_func, exists
from datetime import datetime, timezone

from app.models.global_chat import (
    GlobalChatMessage,
    UserBlock,
    HiddenGlobalChatMessage,
    MessageType
)
from app.schemas.global_chat import GlobalChatMessageCreate


def create_message(
    db: Session,
    user_id: int,
    message_data: GlobalChatMessageCreate
) -> GlobalChatMessage:
    """Создание нового сообщения в глобальном чате"""
    # Преобразуем attachments в JSON
    attachments_json = None
    if message_data.attachments:
        attachments_json = [att.model_dump() for att in message_data.attachments]
    
    message = GlobalChatMessage(
        user_id=user_id,
        message=message_data.message,
        message_type=message_data.message_type,
        attachments=attachments_json,
        extra_metadata=message_data.extra_metadata
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_message_by_id(db: Session, message_id: int) -> Optional[GlobalChatMessage]:
    """Получение сообщения по ID"""
    return db.query(GlobalChatMessage).filter(
        and_(
            GlobalChatMessage.id == message_id,
            GlobalChatMessage.deleted_at.is_(None)  # Не удаленные
        )
    ).first()


def get_messages(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[GlobalChatMessage], int]:
    """
    Получение сообщений глобального чата для пользователя
    
    Исключает:
    - Удаленные сообщения (deleted_at IS NOT NULL)
    - Сообщения от заблокированных пользователей
    - Скрытые сообщения для этого пользователя
    """
    # Базовый запрос
    query = db.query(GlobalChatMessage).filter(
        GlobalChatMessage.deleted_at.is_(None)  # Не удаленные
    )
    
    # Исключаем сообщения от заблокированных пользователей
    query = query.filter(
        ~exists().where(
            and_(
                UserBlock.blocker_id == user_id,
                UserBlock.blocked_id == GlobalChatMessage.user_id
            )
        )
    )
    
    # Исключаем скрытые сообщения
    query = query.filter(
        ~exists().where(
            and_(
                HiddenGlobalChatMessage.message_id == GlobalChatMessage.id,
                HiddenGlobalChatMessage.user_id == user_id
            )
        )
    )
    
    total = query.count()
    messages = query.order_by(GlobalChatMessage.created_at.desc()).offset(skip).limit(limit).all()
    
    return messages, total


def search_messages(
    db: Session,
    user_id: int,
    query_text: str,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[GlobalChatMessage], int]:
    """Поиск сообщений в глобальном чате"""
    # Поиск по тексту сообщения
    search_query = db.query(GlobalChatMessage).filter(
        and_(
            GlobalChatMessage.deleted_at.is_(None),
            GlobalChatMessage.message.ilike(f"%{query_text}%")
        )
    )
    
    # Исключаем сообщения от заблокированных пользователей
    search_query = search_query.filter(
        ~exists().where(
            and_(
                UserBlock.blocker_id == user_id,
                UserBlock.blocked_id == GlobalChatMessage.user_id
            )
        )
    )
    
    # Исключаем скрытые сообщения
    search_query = search_query.filter(
        ~exists().where(
            and_(
                HiddenGlobalChatMessage.message_id == GlobalChatMessage.id,
                HiddenGlobalChatMessage.user_id == user_id
            )
        )
    )
    
    total = search_query.count()
    messages = search_query.order_by(GlobalChatMessage.created_at.desc()).offset(skip).limit(limit).all()
    
    return messages, total


def block_user(
    db: Session,
    blocker_id: int,
    blocked_id: int
) -> Optional[UserBlock]:
    """Блокировка пользователя"""
    # Проверяем, не заблокирован ли уже
    existing = db.query(UserBlock).filter(
        and_(
            UserBlock.blocker_id == blocker_id,
            UserBlock.blocked_id == blocked_id
        )
    ).first()
    
    if existing:
        return existing
    
    # Нельзя заблокировать самого себя
    if blocker_id == blocked_id:
        return None
    
    user_block = UserBlock(
        blocker_id=blocker_id,
        blocked_id=blocked_id
    )
    db.add(user_block)
    db.commit()
    db.refresh(user_block)
    return user_block


def unblock_user(
    db: Session,
    blocker_id: int,
    blocked_id: int
) -> bool:
    """Разблокировка пользователя"""
    user_block = db.query(UserBlock).filter(
        and_(
            UserBlock.blocker_id == blocker_id,
            UserBlock.blocked_id == blocked_id
        )
    ).first()
    
    if not user_block:
        return False
    
    db.delete(user_block)
    db.commit()
    return True


def get_blocked_users(
    db: Session,
    user_id: int
) -> List[UserBlock]:
    """Получение списка заблокированных пользователей"""
    return db.query(UserBlock).filter(
        UserBlock.blocker_id == user_id
    ).order_by(UserBlock.created_at.desc()).all()


def is_user_blocked(
    db: Session,
    blocker_id: int,
    blocked_id: int
) -> bool:
    """Проверка, заблокирован ли пользователь"""
    return db.query(UserBlock).filter(
        and_(
            UserBlock.blocker_id == blocker_id,
            UserBlock.blocked_id == blocked_id
        )
    ).first() is not None


def hide_message_for_user(
    db: Session,
    message_id: int,
    user_id: int
) -> Optional[HiddenGlobalChatMessage]:
    """Скрытие сообщения для конкретного пользователя"""
    # Проверяем, не скрыто ли уже
    existing = db.query(HiddenGlobalChatMessage).filter(
        and_(
            HiddenGlobalChatMessage.message_id == message_id,
            HiddenGlobalChatMessage.user_id == user_id
        )
    ).first()
    
    if existing:
        return existing
    
    hidden = HiddenGlobalChatMessage(
        message_id=message_id,
        user_id=user_id
    )
    db.add(hidden)
    db.commit()
    db.refresh(hidden)
    return hidden


def clear_chat_history_for_user(
    db: Session,
    user_id: int
) -> int:
    """
    Очистка истории чата для конкретного пользователя
    
    Скрывает все сообщения для этого пользователя
    """
    # Получаем все сообщения, которые еще не скрыты
    all_messages = db.query(GlobalChatMessage.id).filter(
        GlobalChatMessage.deleted_at.is_(None)
    ).all()
    
    count = 0
    for (message_id,) in all_messages:
        # Проверяем, не скрыто ли уже
        existing = db.query(HiddenGlobalChatMessage).filter(
            and_(
                HiddenGlobalChatMessage.message_id == message_id,
                HiddenGlobalChatMessage.user_id == user_id
            )
        ).first()
        
        if not existing:
            hidden = HiddenGlobalChatMessage(
                message_id=message_id,
                user_id=user_id
            )
            db.add(hidden)
            count += 1
    
    db.commit()
    return count


def delete_message(
    db: Session,
    message_id: int,
    user_id: int
) -> bool:
    """
    Удаление сообщения (мягкое удаление для всех)
    
    Только автор сообщения может его удалить
    """
    message = get_message_by_id(db, message_id)
    
    if not message or message.user_id != user_id:
        return False
    
    message.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True

