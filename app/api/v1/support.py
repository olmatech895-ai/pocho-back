"""
API эндпоинты для технической поддержки
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user, get_current_admin_user
from app.services.support_service.crud import (
    create_ticket,
    get_ticket_by_id,
    get_user_tickets,
    get_all_tickets,
    update_ticket,
    add_message,
    get_ticket_messages,
    mark_ticket_as_read,
    get_unread_tickets_count,
    get_ticket_stats,
)
from app.schemas.support import (
    SupportTicketCreate,
    SupportTicketUpdate,
    SupportTicketResponse,
    SupportTicketWithMessagesResponse,
    SupportTicketListResponse,
    SupportTicketStatsResponse,
    SupportMessageCreate,
    SupportMessageResponse,
)
from app.models.support import TicketStatus

router = APIRouter()


# Менеджер WebSocket соединений для поддержки
class SupportConnectionManager:
    """Менеджер WebSocket соединений для чата поддержки"""
    
    def __init__(self):
        # Словарь: ticket_id -> список WebSocket соединений
        self.ticket_connections: dict[int, list[WebSocket]] = {}
        # Словарь: user_id -> список WebSocket соединений (для уведомлений о новых тикетах)
        self.user_connections: dict[int, list[WebSocket]] = {}
        # Список администраторов
        self.admin_connections: list[WebSocket] = []
    
    async def connect_to_ticket(self, websocket: WebSocket, ticket_id: int, user_id: int, is_admin: bool = False):
        """Подключение к чату тикета"""
        await websocket.accept()
        
        if ticket_id not in self.ticket_connections:
            self.ticket_connections[ticket_id] = []
        self.ticket_connections[ticket_id].append(websocket)
        
        # Также добавляем в общий список пользователя/админа
        if is_admin:
            if websocket not in self.admin_connections:
                self.admin_connections.append(websocket)
        else:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            if websocket not in self.user_connections[user_id]:
                self.user_connections[user_id].append(websocket)
    
    def disconnect_from_ticket(self, websocket: WebSocket, ticket_id: int, user_id: int, is_admin: bool = False):
        """Отключение от чата тикета"""
        if ticket_id in self.ticket_connections:
            if websocket in self.ticket_connections[ticket_id]:
                self.ticket_connections[ticket_id].remove(websocket)
            if not self.ticket_connections[ticket_id]:
                del self.ticket_connections[ticket_id]
        
        if is_admin:
            if websocket in self.admin_connections:
                self.admin_connections.remove(websocket)
        else:
            if user_id in self.user_connections:
                if websocket in self.user_connections[user_id]:
                    self.user_connections[user_id].remove(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
    
    async def send_message_to_ticket(self, ticket_id: int, message: dict):
        """Отправка сообщения в чат тикета"""
        if ticket_id in self.ticket_connections:
            disconnected = []
            for connection in self.ticket_connections[ticket_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            
            # Удаляем отключенные соединения
            for conn in disconnected:
                self.ticket_connections[ticket_id].remove(conn)
    
    async def notify_new_ticket(self, user_id: int, ticket_data: dict):
        """Уведомление пользователя о новом тикете"""
        if user_id in self.user_connections:
            disconnected = []
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json({
                        "type": "new_ticket",
                        "ticket": ticket_data
                    })
                except Exception:
                    disconnected.append(connection)
            
            for conn in disconnected:
                self.user_connections[user_id].remove(conn)
    
    async def notify_new_message_to_admins(self, ticket_data: dict):
        """Уведомление администраторов о новом сообщении"""
        disconnected = []
        for connection in self.admin_connections:
            try:
                await connection.send_json({
                    "type": "new_message",
                    "ticket": ticket_data
                })
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            if conn in self.admin_connections:
                self.admin_connections.remove(conn)


# Глобальный менеджер соединений
support_manager = SupportConnectionManager()


@router.websocket("/ws/ticket/{ticket_id}")
async def websocket_ticket_chat(
    websocket: WebSocket,
    ticket_id: int,
    token: str = None
):
    """
    WebSocket эндпоинт для чата тикета
    
    Подключение: ws://127.0.0.1:8000/api/v1/support/ws/ticket/{ticket_id}?token=<jwt_token>
    """
    user_id = None
    is_admin = False
    db = None
    
    try:
        # Валидация токена
        if token:
            from jose import jwt
            from app.core.config import settings
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                sub = payload.get("sub")
                if isinstance(sub, str) and ":" in sub:
                    user_id = int(sub.split(":")[1])
                    # Получаем информацию о пользователе для проверки is_admin
                    db = next(get_db())
                    try:
                        from app.crud.user import get_user_by_id
                        user = get_user_by_id(db, user_id)
                        if user:
                            is_admin = user.is_admin
                    finally:
                        db.close()
                else:
                    from app.crud.user import get_user_by_phone_number
                    db = next(get_db())
                    try:
                        user = get_user_by_phone_number(db, sub)
                        if user:
                            user_id = user.id
                            is_admin = user.is_admin
                    finally:
                        db.close()
            except Exception as e:
                print(f"WebSocket auth error: {str(e)}")
                if db:
                    db.close()
                await websocket.close(code=1008, reason="Invalid token")
                return
        
        if not user_id:
            await websocket.close(code=1008, reason="Unauthorized")
            return
        
        # Проверка доступа к тикету
        db = next(get_db())
        try:
            ticket = get_ticket_by_id(db, ticket_id)
            if not ticket:
                await websocket.close(code=1008, reason="Ticket not found")
                return
            
            if not is_admin and ticket.user_id != user_id:
                await websocket.close(code=1008, reason="Access denied")
                return
        finally:
            if db:
                try:
                    db.close()
                except:
                    pass
                db = None
        
        # Подключаемся
        await support_manager.connect_to_ticket(websocket, ticket_id, user_id, is_admin)
        
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "ticket_id": ticket_id,
            "user_id": user_id,
            "is_admin": is_admin
        })
        
        # Ожидаем сообщения
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        if db:
            try:
                db.close()
            except:
                pass
        try:
            support_manager.disconnect_from_ticket(websocket, ticket_id, user_id, is_admin)
        except:
            pass


# ==================== User Endpoints ====================

@router.post("", response_model=SupportTicketResponse)
async def create_support_ticket(
    ticket_data: SupportTicketCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание нового тикета поддержки"""
    ticket = create_ticket(db, current_user.id, ticket_data)
    
    # Уведомляем администраторов через WebSocket
    ticket_response = SupportTicketResponse.model_validate(ticket)
    await support_manager.notify_new_message_to_admins(ticket_response.model_dump())
    
    return ticket_response


@router.get("", response_model=SupportTicketListResponse)
async def get_my_tickets(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[TicketStatus] = Query(None)
):
    """Получение списка тикетов текущего пользователя"""
    tickets, total = get_user_tickets(db, current_user.id, skip=skip, limit=limit, status=status)
    
    return SupportTicketListResponse(
        tickets=[SupportTicketResponse.model_validate(t) for t in tickets],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{ticket_id}", response_model=SupportTicketWithMessagesResponse)
async def get_ticket_with_messages(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение тикета с сообщениями"""
    ticket = get_ticket_by_id(db, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тикет не найден"
        )
    
    if ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен"
        )
    
    messages = get_ticket_messages(db, ticket_id, current_user.id, is_admin=False)
    
    # Отмечаем как прочитанный
    mark_ticket_as_read(db, ticket_id, current_user.id, is_admin=False)
    
    response = SupportTicketWithMessagesResponse.model_validate(ticket)
    # Парсим attachments из JSON
    parsed_messages = []
    for m in messages:
        msg_dict = {
            "id": m.id,
            "ticket_id": m.ticket_id,
            "user_id": m.user_id,
            "is_from_user": m.is_from_user,
            "message": m.message,
            "created_at": m.created_at,
            "attachments": json.loads(m.attachments) if m.attachments else None
        }
        parsed_messages.append(SupportMessageResponse(**msg_dict))
    response.messages = parsed_messages
    
    return response


@router.post("/{ticket_id}/messages", response_model=SupportMessageResponse)
async def send_message(
    ticket_id: int,
    message_data: SupportMessageCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отправка сообщения в тикет"""
    message = add_message(db, ticket_id, current_user.id, message_data, is_from_user=True)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тикет не найден или доступ запрещен"
        )
    
    # Отправляем через WebSocket
    msg_dict = {
        "id": message.id,
        "ticket_id": message.ticket_id,
        "user_id": message.user_id,
        "is_from_user": message.is_from_user,
        "message": message.message,
        "created_at": message.created_at.isoformat(),
        "attachments": json.loads(message.attachments) if message.attachments else None
    }
    message_response = SupportMessageResponse(**msg_dict)
    await support_manager.send_message_to_ticket(
        ticket_id,
        {
            "type": "new_message",
            "message": msg_dict
        }
    )
    
    # Уведомляем администраторов
    ticket = get_ticket_by_id(db, ticket_id)
    if ticket:
        ticket_response = SupportTicketResponse.model_validate(ticket)
        await support_manager.notify_new_message_to_admins(ticket_response.model_dump())
    
    return message_response


@router.post("/{ticket_id}/read", response_model=dict)
async def mark_my_ticket_as_read(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отметить тикет как прочитанный"""
    ticket = mark_ticket_as_read(db, ticket_id, current_user.id, is_admin=False)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тикет не найден или доступ запрещен"
        )
    
    return {
        "success": True,
        "message": "Тикет отмечен как прочитанный"
    }


# ==================== Admin Endpoints ====================

@router.get("/admin/tickets", response_model=SupportTicketListResponse)
async def get_all_support_tickets(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[TicketStatus] = Query(None),
    assigned_to: Optional[int] = Query(None, description="ID администратора (0 для неназначенных)"),
    user_id: Optional[int] = Query(None, description="ID пользователя")
):
    """Получение всех тикетов (для администратора)"""
    tickets, total = get_all_tickets(db, skip=skip, limit=limit, status=status, assigned_to=assigned_to, user_id=user_id)
    
    return SupportTicketListResponse(
        tickets=[SupportTicketResponse.model_validate(t) for t in tickets],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/admin/tickets/{ticket_id}", response_model=SupportTicketWithMessagesResponse)
async def get_admin_ticket_with_messages(
    ticket_id: int,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение тикета с сообщениями (для администратора)"""
    ticket = get_ticket_by_id(db, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тикет не найден"
        )
    
    messages = get_ticket_messages(db, ticket_id, current_admin.id, is_admin=True)
    
    # Отмечаем как прочитанный для администратора
    mark_ticket_as_read(db, ticket_id, current_admin.id, is_admin=True)
    
    response = SupportTicketWithMessagesResponse.model_validate(ticket)
    response.messages = [SupportMessageResponse.model_validate(m) for m in messages]
    
    return response


@router.post("/admin/tickets/{ticket_id}/messages", response_model=SupportMessageResponse)
async def send_admin_message(
    ticket_id: int,
    message_data: SupportMessageCreate,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отправка сообщения администратором"""
    message = add_message(db, ticket_id, current_admin.id, message_data, is_from_user=False)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тикет не найден"
        )
    
    # Отправляем через WebSocket
    msg_dict = {
        "id": message.id,
        "ticket_id": message.ticket_id,
        "user_id": message.user_id,
        "is_from_user": message.is_from_user,
        "message": message.message,
        "created_at": message.created_at.isoformat(),
        "attachments": json.loads(message.attachments) if message.attachments else None
    }
    message_response = SupportMessageResponse(**msg_dict)
    await support_manager.send_message_to_ticket(
        ticket_id,
        {
            "type": "new_message",
            "message": msg_dict
        }
    )
    
    # Уведомляем пользователя
    ticket = get_ticket_by_id(db, ticket_id)
    if ticket:
        ticket_response = SupportTicketResponse.model_validate(ticket)
        await support_manager.notify_new_ticket(ticket.user_id, ticket_response.model_dump())
    
    return message_response


@router.patch("/admin/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def update_support_ticket(
    ticket_id: int,
    ticket_update: SupportTicketUpdate,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление тикета (статус, приоритет, назначение)"""
    ticket = update_ticket(db, ticket_id, ticket_update)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тикет не найден"
        )
    
    return SupportTicketResponse.model_validate(ticket)


@router.post("/admin/tickets/{ticket_id}/read", response_model=dict)
async def mark_admin_ticket_as_read(
    ticket_id: int,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отметить тикет как прочитанный (администратор)"""
    ticket = mark_ticket_as_read(db, ticket_id, current_admin.id, is_admin=True)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тикет не найден"
        )
    
    return {
        "success": True,
        "message": "Тикет отмечен как прочитанный"
    }


@router.get("/admin/stats", response_model=SupportTicketStatsResponse)
async def get_support_stats(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение статистики тикетов"""
    stats = get_ticket_stats(db)
    return SupportTicketStatsResponse(**stats)

