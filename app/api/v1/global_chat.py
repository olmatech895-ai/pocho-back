"""
API эндпоинты для глобального чата
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect, UploadFile, File
from sqlalchemy.orm import Session
import json
import os
import uuid
from pathlib import Path
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.global_chat_service.crud import (
    create_message,
    get_messages,
    search_messages,
    block_user,
    unblock_user,
    get_blocked_users as get_blocked_users_crud,
    clear_chat_history_for_user,
    delete_message,
)
from app.schemas.global_chat import (
    GlobalChatMessageCreate,
    GlobalChatMessageResponse,
    GlobalChatMessageListResponse,
    GlobalChatSearchResponse,
    UserBlockCreate,
    UserBlockResponse,
    BlockedUsersListResponse,
    OnlineUsersResponse,
    AttachmentInfo,
    MessageType,
)
from app.core.config import settings

router = APIRouter()

# Директория для загрузки файлов чата
CHAT_UPLOAD_DIR = Path(settings.UPLOAD_DIR) / "global_chat"
CHAT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Поддиректории для разных типов файлов
CHAT_IMAGES_DIR = CHAT_UPLOAD_DIR / "images"
CHAT_VIDEOS_DIR = CHAT_UPLOAD_DIR / "videos"
CHAT_FILES_DIR = CHAT_UPLOAD_DIR / "files"
CHAT_AUDIO_DIR = CHAT_UPLOAD_DIR / "audio"

CHAT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
CHAT_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
CHAT_FILES_DIR.mkdir(parents=True, exist_ok=True)
CHAT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


# Менеджер WebSocket соединений для глобального чата
class GlobalChatConnectionManager:
    """Менеджер WebSocket соединений для глобального чата"""
    
    def __init__(self):
        # Словарь: user_id -> WebSocket соединение
        self.active_connections: dict[int, WebSocket] = {}
        # Счетчик онлайн пользователей
        self.online_count = 0
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Подключение пользователя к глобальному чату"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.online_count += 1
            # Уведомляем всех о новом пользователе онлайн
            await self.broadcast_online_count()
        
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: int):
        """Отключение пользователя от глобального чата"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            self.online_count = max(0, self.online_count - 1)
    
    async def send_message(self, message_data: dict, exclude_user_id: Optional[int] = None):
        """Отправка сообщения всем подключенным пользователям"""
        disconnected = []
        
        for user_id, connection in list(self.active_connections.items()):
            if exclude_user_id and user_id == exclude_user_id:
                continue
            
            try:
                await connection.send_json({
                    "type": "new_message",
                    "message": message_data
                })
            except Exception:
                disconnected.append(user_id)
        
        # Удаляем отключенные соединения
        for user_id in disconnected:
            self.disconnect(user_id)
        
        # Обновляем счетчик онлайн
        if disconnected:
            await self.broadcast_online_count()
    
    async def broadcast_online_count(self):
        """Отправка обновленного количества онлайн пользователей"""
        message = {
            "type": "online_count",
            "online_count": self.online_count,
            "timestamp": datetime.now().isoformat()
        }
        
        disconnected = []
        for user_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(user_id)
        
        for user_id in disconnected:
            self.disconnect(user_id)
    
    def get_online_count(self) -> int:
        """Получение текущего количества онлайн пользователей"""
        return len(self.active_connections)


# Глобальный менеджер соединений
global_chat_manager = GlobalChatConnectionManager()


def save_chat_file(file: UploadFile, file_type: str, user_id: int) -> str:
    """Сохранение файла для глобального чата"""
    # Определяем директорию по типу файла
    if file_type == "image":
        upload_dir = CHAT_IMAGES_DIR
    elif file_type == "video":
        upload_dir = CHAT_VIDEOS_DIR
    elif file_type == "audio":
        upload_dir = CHAT_AUDIO_DIR
    else:
        upload_dir = CHAT_FILES_DIR
    
    # Генерируем уникальное имя файла
    file_extension = Path(file.filename).suffix if file.filename else ".bin"
    unique_filename = f"{user_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = upload_dir / unique_filename
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    # Генерируем URL
    relative_path = f"{settings.UPLOAD_DIR}/global_chat/{upload_dir.name}/{unique_filename}"
    return f"{settings.BASE_URL}/{relative_path}"


@router.websocket("/ws")
async def websocket_global_chat(websocket: WebSocket, token: str = None):
    """
    WebSocket эндпоинт для глобального чата
    
    Подключение: ws://127.0.0.1:8000/api/v1/global-chat/ws?token=<jwt_token>
    """
    user_id = None
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
                else:
                    from app.crud.user import get_user_by_phone_number
                    db = next(get_db())
                    try:
                        user = get_user_by_phone_number(db, sub)
                        if user:
                            user_id = user.id
                    finally:
                        if db:
                            db.close()
                            db = None
            except Exception as e:
                print(f"WebSocket auth error: {str(e)}")
                await websocket.close(code=1008, reason="Invalid token")
                return
        
        if not user_id:
            await websocket.close(code=1008, reason="Unauthorized")
            return
        
        # Подключаемся
        await global_chat_manager.connect(websocket, user_id)
        
        # Отправляем приветственное сообщение
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "online_count": global_chat_manager.get_online_count(),
            "message": "Подключено к глобальному чату"
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
        if user_id:
            global_chat_manager.disconnect(user_id)
            # Уведомляем остальных об изменении количества онлайн
            await global_chat_manager.broadcast_online_count()


# ==================== REST API Endpoints ====================

@router.post("/messages", response_model=GlobalChatMessageResponse)
async def send_message(
    message_data: GlobalChatMessageCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отправка сообщения в глобальный чат"""
    message = create_message(db, current_user.id, message_data)
    
    # Получаем информацию о пользователе
    from app.services.user_service.crud import get_user_extended_by_id
    user_extended = get_user_extended_by_id(db, current_user.id)
    
    # Формируем ответ
    message_response = GlobalChatMessageResponse(
        id=message.id,
        user_id=message.user_id,
        user_name=user_extended.name if user_extended else None,
        user_avatar=user_extended.avatar if user_extended else None,
        message=message.message,
        message_type=message.message_type,
        attachments=message.attachments,
        extra_metadata=message.extra_metadata,
        created_at=message.created_at,
        updated_at=message.updated_at
    )
    
    # Отправляем через WebSocket всем подключенным
    await global_chat_manager.send_message(
        message_response.model_dump(),
        exclude_user_id=current_user.id  # Отправитель уже видит свое сообщение
    )
    
    return message_response


@router.post("/messages/upload", response_model=dict)
async def upload_file(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    file_type: str = Query(..., description="Тип файла: image, video, audio, file")
):
    """Загрузка файла для глобального чата"""
    # Проверка типа файла
    allowed_types = ["image", "video", "audio", "file"]
    if file_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый тип файла. Разрешены: {', '.join(allowed_types)}"
        )
    
    # Проверка размера файла
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    max_size = 50 * 1024 * 1024  # 50 MB
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл слишком большой. Максимальный размер: {max_size / 1024 / 1024}MB"
        )
    
    # Сохраняем файл
    try:
        file_url = save_chat_file(file, file_type, current_user.id)
        
        # Определяем MessageType
        message_type_map = {
            "image": MessageType.IMAGE,
            "video": MessageType.VIDEO,
            "audio": MessageType.AUDIO,
            "file": MessageType.FILE
        }
        
        attachment_info = AttachmentInfo(
            url=file_url,
            type=file_type,
            name=file.filename,
            size=file_size
        )
        
        return {
            "success": True,
            "file_url": file_url,
            "attachment": attachment_info.model_dump(),
            "message_type": message_type_map[file_type].value
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке файла: {str(e)}"
        )


@router.get("/messages", response_model=GlobalChatMessageListResponse)
async def get_chat_messages(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Получение сообщений глобального чата"""
    messages, total = get_messages(db, current_user.id, skip=skip, limit=limit)
    
    # Получаем информацию о пользователях
    from app.services.user_service.crud import get_user_extended_by_id
    
    messages_response = []
    for msg in messages:
        user_extended = get_user_extended_by_id(db, msg.user_id)
        messages_response.append(GlobalChatMessageResponse(
            id=msg.id,
            user_id=msg.user_id,
            user_name=user_extended.name if user_extended else None,
            user_avatar=user_extended.avatar if user_extended else None,
            message=msg.message,
            message_type=msg.message_type,
            attachments=msg.attachments,
            extra_metadata=msg.extra_metadata,
            created_at=msg.created_at,
            updated_at=msg.updated_at
        ))
    
    return GlobalChatMessageListResponse(
        messages=messages_response,
        total=total,
        skip=skip,
        limit=limit,
        online_count=global_chat_manager.get_online_count()
    )


@router.get("/messages/search", response_model=GlobalChatSearchResponse)
async def search_chat_messages(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    query: str = Query(..., min_length=1, description="Поисковый запрос"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Поиск сообщений в глобальном чате"""
    messages, total = search_messages(db, current_user.id, query, skip=skip, limit=limit)
    
    # Получаем информацию о пользователях
    from app.services.user_service.crud import get_user_extended_by_id
    
    messages_response = []
    for msg in messages:
        user_extended = get_user_extended_by_id(db, msg.user_id)
        messages_response.append(GlobalChatMessageResponse(
            id=msg.id,
            user_id=msg.user_id,
            user_name=user_extended.name if user_extended else None,
            user_avatar=user_extended.avatar if user_extended else None,
            message=msg.message,
            message_type=msg.message_type,
            attachments=msg.attachments,
            extra_metadata=msg.extra_metadata,
            created_at=msg.created_at,
            updated_at=msg.updated_at
        ))
    
    return GlobalChatSearchResponse(
        messages=messages_response,
        total=total,
        query=query,
        skip=skip,
        limit=limit
    )


@router.get("/online", response_model=OnlineUsersResponse)
async def get_online_count(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Получение количества пользователей онлайн"""
    return OnlineUsersResponse(
        online_count=global_chat_manager.get_online_count(),
        timestamp=datetime.now()
    )


@router.post("/block", response_model=UserBlockResponse)
async def block_user_endpoint(
    block_data: UserBlockCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Заблокировать пользователя"""
    user_block = block_user(db, current_user.id, block_data.blocked_user_id)
    
    if not user_block:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось заблокировать пользователя (возможно, уже заблокирован или попытка заблокировать себя)"
        )
    
    # Получаем информацию о заблокированном пользователе
    from app.services.user_service.crud import get_user_extended_by_id
    blocked_user_extended = get_user_extended_by_id(db, block_data.blocked_user_id)
    
    return UserBlockResponse(
        id=user_block.id,
        blocker_id=user_block.blocker_id,
        blocked_id=user_block.blocked_id,
        blocked_user_name=blocked_user_extended.name if blocked_user_extended else None,
        created_at=user_block.created_at
    )


@router.delete("/block/{blocked_user_id}", response_model=dict)
async def unblock_user_endpoint(
    blocked_user_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Разблокировать пользователя"""
    success = unblock_user(db, current_user.id, blocked_user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден в списке заблокированных"
        )
    
    return {
        "success": True,
        "message": "Пользователь разблокирован"
    }


@router.get("/blocked", response_model=BlockedUsersListResponse)
async def get_blocked_users(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение списка заблокированных пользователей"""
    blocked_list = get_blocked_users_crud(db, current_user.id)
    
    # Получаем информацию о пользователях
    from app.services.user_service.crud import get_user_extended_by_id
    
    blocked_response = []
    for block in blocked_list:
        blocked_user_extended = get_user_extended_by_id(db, block.blocked_id)
        blocked_response.append(UserBlockResponse(
            id=block.id,
            blocker_id=block.blocker_id,
            blocked_id=block.blocked_id,
            blocked_user_name=blocked_user_extended.name if blocked_user_extended else None,
            created_at=block.created_at
        ))
    
    return BlockedUsersListResponse(
        blocked_users=blocked_response,
        total=len(blocked_response)
    )


@router.delete("/messages/history", response_model=dict)
async def clear_chat_history(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Очистка истории чата для текущего пользователя (только для него)"""
    count = clear_chat_history_for_user(db, current_user.id)
    
    return {
        "success": True,
        "message": f"История чата очищена ({count} сообщений скрыто)",
        "count": count
    }


@router.delete("/messages/{message_id}", response_model=dict)
async def delete_chat_message(
    message_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление сообщения (только автор может удалить, удаляется для всех)"""
    success = delete_message(db, message_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сообщение не найдено или у вас нет прав на его удаление"
        )
    
    # Уведомляем всех через WebSocket об удалении
    await global_chat_manager.send_message({
        "type": "message_deleted",
        "message_id": message_id
    })
    
    return {
        "success": True,
        "message": "Сообщение удалено",
        "message_id": message_id
    }

