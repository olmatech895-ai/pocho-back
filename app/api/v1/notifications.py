"""
API эндпоинты для уведомлений пользователей
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.notification_service.crud import (
    get_user_notifications,
    get_unread_count,
    mark_notification_as_read,
    mark_all_as_read,
    delete_notification,
    delete_all_user_notifications,
    get_notification_by_id,
)
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationStatsResponse,
    NotificationUpdate,
)

router = APIRouter()


# Менеджер WebSocket соединений
class ConnectionManager:
    """Менеджер WebSocket соединений для уведомлений"""
    
    def __init__(self):
        # Словарь: user_id -> список WebSocket соединений
        self.active_connections: dict[int, list[WebSocket]] = {}
        # Список соединений для глобальных уведомлений (все пользователи)
        self.global_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """Подключение пользователя к WebSocket"""
        await websocket.accept()
        
        if user_id:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
        else:
            self.global_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """Отключение пользователя от WebSocket"""
        if user_id and user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        else:
            if websocket in self.global_connections:
                self.global_connections.remove(websocket)
    
    async def send_personal_notification(self, user_id: int, message: dict):
        """Отправка персонального уведомления пользователю"""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            
            # Удаляем отключенные соединения
            for conn in disconnected:
                self.active_connections[user_id].remove(conn)
    
    async def send_global_notification(self, message: dict):
        """Отправка глобального уведомления всем пользователям"""
        disconnected = []
        for connection in self.global_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Также отправляем всем персональным соединениям
        for user_id, connections in list(self.active_connections.items()):
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    if connection in connections:
                        connections.remove(connection)
        
        # Удаляем отключенные соединения
        for conn in disconnected:
            if conn in self.global_connections:
                self.global_connections.remove(conn)


# Глобальный менеджер соединений
manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = None):
    """
    WebSocket эндпоинт для получения уведомлений в реальном времени
    
    Подключение: ws://127.0.0.1:8000/api/v1/notifications/ws/notifications?token=<jwt_token>
    
    После подключения пользователь будет получать уведомления в реальном времени:
    - Персональные уведомления (только для этого пользователя)
    - Глобальные уведомления (для всех пользователей)
    """
    user_id = None
    
    try:
        # Валидация токена (упрощенная версия)
        if token:
            from jose import jwt
            from app.core.config import settings
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                # Извлекаем user_id из токена
                sub = payload.get("sub")
                if isinstance(sub, str) and ":" in sub:
                    user_id = int(sub.split(":")[1])
                elif isinstance(sub, dict):
                    user_id = sub.get("id")
                else:
                    # Старый формат - только phone_number
                    from app.crud.user import get_user_by_phone_number
                    db = next(get_db())
                    try:
                        user = get_user_by_phone_number(db, sub)
                        if user:
                            user_id = user.id
                    finally:
                        db.close()
            except Exception as e:
                print(f"WebSocket auth error: {str(e)}")
                await websocket.close(code=1008, reason="Invalid token")
                return
        
        # Подключаем пользователя
        await manager.connect(websocket, user_id)
        
        # Отправляем приветственное сообщение
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "message": "Подключено к системе уведомлений"
        })
        
        # Ожидаем сообщения от клиента (для поддержания соединения)
        while True:
            try:
                data = await websocket.receive_text()
                # Можно обрабатывать команды от клиента (например, ping/pong)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        manager.disconnect(websocket, user_id)


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    unread_only: Optional[bool] = Query(None, description="Только непрочитанные уведомления")
):
    """
    Получение списка уведомлений пользователя
    
    Включает:
    - Персональные уведомления (созданные специально для этого пользователя)
    - Глобальные уведомления (для всех пользователей)
    """
    try:
        notifications, total = get_user_notifications(
            db,
            current_user.id,
            skip=skip,
            limit=limit,
            unread_only=unread_only
        )
        
        unread_count = get_unread_count(db, current_user.id)
        
        return NotificationListResponse(
            notifications=[NotificationResponse.model_validate(n) for n in notifications],
            total=total,
            unread_count=unread_count,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        import traceback
        print(f"Error getting notifications: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении уведомлений"
        )


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение статистики уведомлений пользователя"""
    try:
        all_notifications, total = get_user_notifications(db, current_user.id, skip=0, limit=10000)
        unread = get_unread_count(db, current_user.id)
        read = total - unread
        
        return NotificationStatsResponse(
            total=total,
            unread=unread,
            read=read
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении статистики уведомлений"
        )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отметить уведомление как прочитанное"""
    notification = mark_notification_as_read(db, notification_id, current_user.id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Уведомление не найдено или недоступно"
        )
    
    return NotificationResponse.model_validate(notification)


@router.post("/read-all", response_model=dict)
async def mark_all_notifications_as_read(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отметить все уведомления как прочитанные"""
    count = mark_all_as_read(db, current_user.id)
    
    return {
        "success": True,
        "message": f"Отмечено {count} уведомлений как прочитанные",
        "count": count
    }


@router.delete("/{notification_id}", response_model=dict)
async def delete_user_notification(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Удаление уведомления пользователем
    
    - Персональные уведомления: удаляются полностью
    - Глобальные уведомления: скрываются для этого пользователя
    """
    deleted = delete_notification(db, notification_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Уведомление не найдено или недоступно для удаления"
        )
    
    notification = get_notification_by_id(db, notification_id)
    if notification and notification.user_id is None:
        message = "Глобальное уведомление скрыто"
    else:
        message = "Уведомление удалено"
    
    return {
        "success": True,
        "message": message,
        "notification_id": notification_id
    }


@router.delete("", response_model=dict)
async def delete_all_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Удаление всех уведомлений пользователя
    
    - Все персональные уведомления удаляются полностью
    - Все глобальные уведомления скрываются для этого пользователя
    """
    count = delete_all_user_notifications(db, current_user.id)
    
    return {
        "success": True,
        "message": f"Удалено {count} уведомлений",
        "count": count
    }
