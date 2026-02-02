"""
API эндпоинты для профиля пользователя
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import os
import uuid
from pathlib import Path

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.profile_service.crud import (
    get_profile_by_user_id,
    create_profile,
    update_profile,
)
from app.services.user_service.crud import get_user_extended_by_id, create_user_extended, update_user_extended
from app.schemas.user_extended import UserExtendedCreate, UserExtendedUpdate
from app.schemas.user_extended import (
    UserProfileResponse,
    UserProfileUpdate,
    ProfileWithUserDataResponse,
    DocumentInfo,
    ProfileDocuments,
    ProfileSettings,
    BalanceInfo,
    UpdateNameRequest,
    UpdateEmailRequest,
    UpdateNotificationsRequest,
    UpdateResponse,
)

router = APIRouter()

# Создаем директорию для загрузки файлов, если её нет
from app.core.config import settings
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PASSPORT_DIR = UPLOAD_DIR / "passports"
DRIVING_LICENSE_DIR = UPLOAD_DIR / "driving_licenses"
AVATAR_DIR = UPLOAD_DIR / "avatars"
PASSPORT_DIR.mkdir(parents=True, exist_ok=True)
DRIVING_LICENSE_DIR.mkdir(parents=True, exist_ok=True)
AVATAR_DIR.mkdir(parents=True, exist_ok=True)


def delete_file_by_url(file_url: str) -> bool:
    """
    Удаление файла по его URL
    
    Args:
        file_url: URL файла (например, http://localhost:8000/uploads/avatars/1_abc123.jpg)
    
    Returns:
        True если файл удален, False если файл не найден
    """
    try:
        # Извлекаем путь к файлу из URL
        if not file_url or not file_url.startswith(settings.BASE_URL):
            return False
        
        # Убираем BASE_URL и получаем относительный путь
        relative_path = file_url.replace(settings.BASE_URL, "")
        if relative_path.startswith("/"):
            relative_path = relative_path[1:]
        
        # Полный путь к файлу
        file_path = Path(relative_path)
        
        # Проверяем существование файла
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True
        return False
    except Exception as e:
        print(f"Error deleting file {file_url}: {str(e)}")
        return False


def save_uploaded_file(file: UploadFile, directory: Path, user_id: int) -> str:
    """
    Сохранение загруженного файла и возврат URL
    
    Args:
        file: Загруженный файл
        directory: Директория для сохранения
        user_id: ID пользователя
    
    Returns:
        URL сохраненного файла
    """
    # Генерируем уникальное имя файла
    file_extension = Path(file.filename).suffix if file.filename else ".jpg"
    unique_filename = f"{user_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = directory / unique_filename
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    # Возвращаем относительный путь для URL
    relative_path = f"/{settings.UPLOAD_DIR}/{directory.name}/{unique_filename}"
    return f"{settings.BASE_URL}{relative_path}"


@router.get("", response_model=ProfileWithUserDataResponse)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Получение профиля пользователя с данными пользователя
    
    Возвращает объединенную структуру:
    - Данные пользователя (id, phone, name, email, avatar, language, balance, level, rating, etc.)
    - Профиль с документами и настройками
    
    Автоматически создает расширенный профиль, если его нет (для старых пользователей).
    """
    user_extended = get_user_extended_by_id(db, current_user.id)
    
    # Если расширенного профиля нет - создаем его автоматически
    if not user_extended:
        try:
            user_extended_data = UserExtendedCreate(
                user_id=current_user.id,
                phone=current_user.phone_number,
                name=current_user.fullname,
                email=None,
                avatar=None,
                language="ru",
                balance=0.0,
                level="Новичок",
                rating=0.0
            )
            user_extended = create_user_extended(db, user_extended_data)
            
            # Создаем связанные данные
            from app.services.notifications_service.crud import create_notifications
            from app.services.statistics_service.crud import create_statistics
            
            create_notifications(db, user_extended.id)
            create_statistics(db, user_extended.id)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error creating extended profile for user {current_user.id}: {str(e)}")
            print(f"Traceback: {error_details}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при создании расширенного профиля"
            )
    
    profile = get_profile_by_user_id(db, user_extended.id)
    if not profile:
        profile = create_profile(db, user_extended.id)
    
    # Преобразуем профиль в нужный формат
    documents = ProfileDocuments(
        passport=DocumentInfo(
            image_url=profile.passport_image_url,
            verified=profile.passport_verified,
            uploaded_at=profile.passport_uploaded_at
        ),
        driving_license=DocumentInfo(
            image_url=profile.driving_license_image_url,
            verified=profile.driving_license_verified,
            uploaded_at=profile.driving_license_uploaded_at
        )
    )
    
    settings = ProfileSettings(**profile.settings if profile.settings else {})
    
    profile_response = UserProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        documents=documents,
        settings=settings,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )
    
    # Создаем информацию о балансе для удобного отображения
    balance_info = BalanceInfo.from_amount(user_extended.balance)
    
    # Возвращаем объединенную структуру
    return ProfileWithUserDataResponse(
        id=user_extended.id,
        phone=user_extended.phone,
        name=user_extended.name,
        email=user_extended.email,
        avatar=user_extended.avatar,
        created_at=user_extended.created_at,
        updated_at=user_extended.updated_at,
        language=user_extended.language,
        balance=user_extended.balance,
        balance_info=balance_info,
        level=user_extended.level,
        rating=user_extended.rating,
        total_stations_visited=user_extended.total_stations_visited,
        total_spent=user_extended.total_spent,
        profile=profile_response
    )


@router.patch("/name", response_model=UpdateResponse)
async def update_user_name(
    request: UpdateNameRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление имени пользователя"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    update_data = UserExtendedUpdate(name=request.name)
    updated_user = update_user_extended(db, current_user.id, update_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении имени"
        )
    
    return UpdateResponse(
        success=True,
        message="Имя успешно обновлено",
        data={"name": updated_user.name}
    )


@router.patch("/email", response_model=UpdateResponse)
async def update_user_email(
    request: UpdateEmailRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление email пользователя"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    # Валидация email (можно добавить более строгую проверку)
    if request.email and "@" not in request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат email"
        )
    
    update_data = UserExtendedUpdate(email=request.email)
    updated_user = update_user_extended(db, current_user.id, update_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении email"
        )
    
    return UpdateResponse(
        success=True,
        message="Email успешно обновлен",
        data={"email": updated_user.email}
    )


@router.patch("/passport", response_model=UpdateResponse)
async def update_passport_photo(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Загрузка фото паспорта"""
    # Проверка типа файла
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый тип файла. Разрешены: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    # Проверка размера файла
    file.file.seek(0, 2)  # Перемещаемся в конец файла
    file_size = file.file.tell()
    file.file.seek(0)  # Возвращаемся в начало
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл слишком большой. Максимальный размер: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    user_extended = get_user_extended_by_id(db, current_user.id)
    
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    profile = get_profile_by_user_id(db, user_extended.id)
    if not profile:
        profile = create_profile(db, user_extended.id)
    
    # Сохраняем файл
    try:
        image_url = save_uploaded_file(file, PASSPORT_DIR, current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при сохранении файла: {str(e)}"
        )
    
    # Обновляем профиль
    profile_update = UserProfileUpdate(
        passport_image_url=image_url,
        passport_verified=False  # После загрузки требуется верификация
    )
    updated_profile = update_profile(db, user_extended.id, profile_update)
    
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении профиля"
        )
    
    return UpdateResponse(
        success=True,
        message="Фото паспорта успешно загружено",
        data={
            "passport_image_url": updated_profile.passport_image_url,
            "passport_verified": updated_profile.passport_verified,
            "uploaded_at": updated_profile.passport_uploaded_at.isoformat() if updated_profile.passport_uploaded_at else None
        }
    )


@router.patch("/driving-license", response_model=UpdateResponse)
async def update_driving_license_photo(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Загрузка фото водительских прав"""
    # Проверка типа файла
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый тип файла. Разрешены: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    # Проверка размера файла
    file.file.seek(0, 2)  # Перемещаемся в конец файла
    file_size = file.file.tell()
    file.file.seek(0)  # Возвращаемся в начало
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл слишком большой. Максимальный размер: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    user_extended = get_user_extended_by_id(db, current_user.id)
    
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    profile = get_profile_by_user_id(db, user_extended.id)
    if not profile:
        profile = create_profile(db, user_extended.id)
    
    # Сохраняем файл
    try:
        image_url = save_uploaded_file(file, DRIVING_LICENSE_DIR, current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при сохранении файла: {str(e)}"
        )
    
    # Обновляем профиль
    profile_update = UserProfileUpdate(
        driving_license_image_url=image_url,
        driving_license_verified=False  # После загрузки требуется верификация
    )
    updated_profile = update_profile(db, user_extended.id, profile_update)
    
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении профиля"
        )
    
    return UpdateResponse(
        success=True,
        message="Фото водительских прав успешно загружено",
        data={
            "driving_license_image_url": updated_profile.driving_license_image_url,
            "driving_license_verified": updated_profile.driving_license_verified,
            "uploaded_at": updated_profile.driving_license_uploaded_at.isoformat() if updated_profile.driving_license_uploaded_at else None
        }
    )


@router.patch("/notifications", response_model=UpdateResponse)
async def update_notifications(
    request: UpdateNotificationsRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Включение/отключение уведомлений"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    profile = get_profile_by_user_id(db, user_extended.id)
    if not profile:
        profile = create_profile(db, user_extended.id)
    
    # Обновляем настройки уведомлений
    current_settings = profile.settings if profile.settings else {}
    current_settings["notifications_enabled"] = request.notifications_enabled
    
    profile_update = UserProfileUpdate(settings=current_settings)
    updated_profile = update_profile(db, user_extended.id, profile_update)
    
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении настроек уведомлений"
        )
    
    return UpdateResponse(
        success=True,
        message="Настройки уведомлений успешно обновлены",
        data={
            "notifications_enabled": updated_profile.settings.get("notifications_enabled", False)
        }
    )


@router.patch("/avatar", response_model=UpdateResponse)
async def update_avatar(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Загрузка/обновление аватара пользователя"""
    # Проверка типа файла
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый тип файла. Разрешены: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    # Проверка размера файла
    file.file.seek(0, 2)  # Перемещаемся в конец файла
    file_size = file.file.tell()
    file.file.seek(0)  # Возвращаемся в начало
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл слишком большой. Максимальный размер: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    user_extended = get_user_extended_by_id(db, current_user.id)
    
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    # Удаляем старый аватар, если он существует
    if user_extended.avatar:
        delete_file_by_url(user_extended.avatar)
    
    # Сохраняем новый файл
    try:
        image_url = save_uploaded_file(file, AVATAR_DIR, current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при сохранении файла: {str(e)}"
        )
    
    # Обновляем профиль
    updated_user = update_user_extended(
        db,
        current_user.id,
        UserExtendedUpdate(avatar=image_url)
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении аватара"
        )
    
    return UpdateResponse(
        success=True,
        message="Аватар успешно обновлен",
        data={
            "avatar": updated_user.avatar
        }
    )

