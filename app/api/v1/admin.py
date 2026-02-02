from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from jose.exceptions import JWTClaimsError, ExpiredSignatureError

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserDeleteRequest,
    UserDeleteResponse,
    UserUpdateAdminRequest,
    UserUpdateBlockRequest,
    UserUpdateResponse,
    UserResponse,
    CreateAdminRequest,
    CreateAdminResponse,
    AdminUpdateUserNameRequest,
    AdminUpdateUserBalanceRequest,
    AdminUpdateUserRatingRequest,
    AdminUpdateUserLevelRequest,
    AdminUpdateUserDocumentsRequest,
    AdminVerifyDocumentRequest,
)
from app.schemas.user_extended import (
    ProfileWithUserDataResponse,
    ProfileDocuments,
    DocumentInfo,
    ProfileSettings,
    BalanceInfo,
    UserProfileResponse,
    UserExtendedUpdate,
    UserProfileUpdate,
    UpdateResponse,
)
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationListResponse,
)
from app.services.notification_service.crud import (
    create_notification,
    get_all_notifications,
    delete_notification_admin,
)
# Импортируем менеджер WebSocket соединений
from app.api.v1.notifications import manager as notification_manager
from pydantic import BaseModel
from app.api.deps import get_current_admin_user
from app.core.config import settings
from app.crud.user import (
    get_user_by_phone_number,
    get_user_by_id,
    is_token_blacklisted,
    has_any_admin,
    delete_user,
    set_admin_status,
    set_block_status,
    create_admin_user,
    check_login_exists,
    get_all_users,
)
from app.core.utils import generate_unique_login, generate_password
from app.core.security import get_password_hash
from app.services.user_service.crud import (
    get_user_extended_by_id,
    update_user_extended,
)
from app.services.profile_service.crud import (
    get_profile_by_user_id,
    create_profile,
    update_profile,
)
from pathlib import Path
import os

router = APIRouter()


def build_profile_response(user: User, db: Session) -> ProfileWithUserDataResponse:
    """
    Создание полного ответа профиля для пользователя
    Аналогично эндпоинту GET /api/v1/profile
    """
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.profile_service.crud import get_profile_by_user_id, create_profile
    
    user_extended = get_user_extended_by_id(db, user.id)
    
    # Если расширенного профиля нет - создаем его автоматически
    if not user_extended:
        try:
            from app.schemas.user_extended import UserExtendedCreate
            from app.services.user_service.crud import create_user_extended
            from app.services.notifications_service.crud import create_notifications
            from app.services.statistics_service.crud import create_statistics
            
            user_extended_data = UserExtendedCreate(
                user_id=user.id,
                phone=user.phone_number,
                name=user.fullname,
                email=None,
                avatar=None,
                language="ru",
                balance=0.0,
                level="Новичок",
                rating=0.0
            )
            user_extended = create_user_extended(db, user_extended_data)
            
            create_notifications(db, user_extended.id)
            create_statistics(db, user_extended.id)
        except Exception as e:
            import traceback
            print(f"Error creating extended profile for user {user.id}: {str(e)}")
            print(traceback.format_exc())
            # Продолжаем с None, если не удалось создать
    
    if not user_extended:
        # Если все еще нет профиля, возвращаем минимальную информацию
        return ProfileWithUserDataResponse(
            id=0,
            phone=user.phone_number,
            name=user.fullname,
            email=None,
            avatar=None,
            created_at=user.created_at,
            updated_at=None,
            language="ru",
            balance=0.0,
            balance_info=BalanceInfo.from_amount(0.0),
            level="Новичок",
            rating=0.0,
            total_stations_visited=0,
            total_spent=0.0,
            profile=None
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


class UsersListResponse(BaseModel):
    """Ответ со списком пользователей с полной информацией профиля"""
    users: List[ProfileWithUserDataResponse]
    total: int
    skip: int
    limit: int


@router.get("/users", response_model=UsersListResponse)
async def get_all_users_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    is_admin: Optional[bool] = Query(None, description="Фильтр по статусу администратора"),
    is_blocked: Optional[bool] = Query(None, description="Фильтр по статусу блокировки"),
    is_active: Optional[bool] = Query(None, description="Фильтр по статусу активности")
):
    """
    Получение списка всех пользователей с полной информацией профиля
    
    Доступно только администраторам.
    Поддерживает пагинацию и фильтрацию по статусам.
    Возвращает полную информацию профиля для каждого пользователя (как в GET /api/v1/profile).
    """
    try:
        users, total = get_all_users(
            db=db,
            skip=skip,
            limit=limit,
            is_admin=is_admin,
            is_blocked=is_blocked,
            is_active=is_active
        )
        
        # Строим полные профили для каждого пользователя
        profiles = [build_profile_response(user, db) for user in users]
        
        return UsersListResponse(
            users=profiles,
            total=total,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        import traceback
        print(f"Error getting users list: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка пользователей"
        )


@router.post(
    "/create-admin",
    response_model=CreateAdminResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_admin(
    request: CreateAdminRequest,
    http_request: Request,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Создание нового администратора с уникальным логином и паролем
    
    Если в базе еще нет админов - позволяет создать первого админа без токена.
    Если админы уже существуют - требует токен администратора в HTTP заголовке Authorization: Bearer <token>.
    
    - **phone_number**: номер телефона для нового администратора
    
    Возвращает:
    - **login**: уникальный логин для входа
    - **password**: сгенерированный пароль (сохраните его!)
    - **user**: информация о созданном пользователе
    
    ⚠️ Внимание: Пароль показывается только один раз при создании!
    
    ⚠️ Токен (если требуется) передается в HTTP заголовке Authorization, а не в body запроса.
    """
    # Проверяем наличие админов в базе
    if has_any_admin(db):
        # Если админы есть - проверяем токен
        auth_header = http_request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Admin token is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = auth_header.replace("Bearer ", "").strip()
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            # Проверяем, не находится ли токен в черном списке
            if is_token_blacklisted(db, token):
                raise credentials_exception
            
            # Декодируем токен с отключенной проверкой sub (для обратной совместимости)
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_sub": False}
            )
            
            # Форматы sub: словарь {phone_number, id}, строка "phone:id", или строка "phone"
            sub = payload.get("sub")
            user_id = payload.get("user_id")
            phone_number_auth = None

            if isinstance(sub, dict):
                phone_number_auth = sub.get("phone_number")
                if not user_id:
                    user_id = sub.get("id")
            elif isinstance(sub, str):
                if ":" in sub:
                    parts = sub.split(":", 1)
                    phone_number_auth = parts[0] if parts[0] else None
                    if not user_id and len(parts) > 1:
                        try:
                            user_id = int(parts[1])
                        except (ValueError, TypeError):
                            pass
                else:
                    phone_number_auth = sub

            if not phone_number_auth and not user_id:
                raise credentials_exception

            # Получаем пользователя
            if user_id:
                admin_user_check = get_user_by_id(db, user_id)
            else:
                admin_user_check = get_user_by_phone_number(db, phone_number_auth)
            
            if admin_user_check is None:
                raise credentials_exception
            
            # Проверяем, что это админ
            if not admin_user_check.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Admin rights required."
                )
            
            # Проверяем активность и блокировку
            if not admin_user_check.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive"
                )
            
            if admin_user_check.is_blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is blocked"
                )
        except JWTError:
            raise credentials_exception
        except HTTPException:
            raise
    
    try:
        phone_number = request.phone_number
        
        # Проверяем, не существует ли уже пользователь с таким номером
        existing_user = get_user_by_phone_number(db, phone_number)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Пользователь с номером {phone_number} уже существует"
            )
        
        # Генерируем уникальный логин
        max_attempts = 10
        login = None
        for _ in range(max_attempts):
            candidate_login = generate_unique_login()
            if not check_login_exists(db, candidate_login):
                login = candidate_login
                break
        
        if not login:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось сгенерировать уникальный логин. Попробуйте позже."
            )
        
        # Генерируем пароль
        password = generate_password()
        hashed_password = get_password_hash(password)
        
        # Создаем администратора
        admin_user = create_admin_user(
            db=db,
            phone_number=phone_number,
            login=login,
            hashed_password=hashed_password,
            fullname=None
        )
        
        return CreateAdminResponse(
            message="Администратор успешно создан",
            phone_number=phone_number,
            login=login,
            password=password,  # Показываем пароль только один раз!
            user=UserResponse.model_validate(admin_user)
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        print(f"Error creating admin: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании администратора"
        )


@router.delete("/user", response_model=UserDeleteResponse)
async def delete_user_account(
    request: UserDeleteRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Удаление регистрации пользователя
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя для удаления
    
    ⚠️ Внимание: Это действие необратимо!
    """
    try:
        phone_number = request.phone_number
        
        # Проверяем, что администратор не удаляет сам себя
        if phone_number == current_admin.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы не можете удалить свой собственный аккаунт"
            )
        
        # Проверяем существование пользователя
        user = get_user_by_phone_number(db, phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        # Удаляем пользователя и все связанные данные
        try:
            deleted = delete_user(db, phone_number)
            
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Ошибка при удалении пользователя"
                )
            
            return UserDeleteResponse(
                message="Пользователь успешно удален",
                phone_number=phone_number,
                deleted=True
            )
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in delete_user_account endpoint: {str(e)}")
            print(f"Traceback: {error_details}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при удалении пользователя: {str(e)}"
            )
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при удалении пользователя"
        )


@router.post("/user/admin", response_model=UserUpdateResponse)
async def set_user_admin(
    request: UserUpdateAdminRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Назначение/снятие прав администратора пользователю
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    - **is_admin**: true для назначения администратором, false для снятия прав
    """
    try:
        phone_number = request.phone_number
        is_admin = request.is_admin
        
        # Проверяем существование пользователя
        user = get_user_by_phone_number(db, phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        # Обновляем статус администратора
        updated_user = set_admin_status(db, phone_number, is_admin)
        
        if updated_user:
            return UserUpdateResponse(
                message=f"Права администратора {'назначены' if is_admin else 'сняты'}",
                user=UserResponse.model_validate(updated_user)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении статуса администратора"
            )
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error updating admin status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении статуса администратора"
        )


@router.post("/user/block", response_model=UserUpdateResponse)
async def block_user(
    request: UserUpdateBlockRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Блокировка/разблокировка пользователя
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    - **is_blocked**: true для блокировки, false для разблокировки
    
    ⚠️ Заблокированные пользователи не смогут авторизоваться в системе
    """
    try:
        phone_number = request.phone_number
        is_blocked = request.is_blocked
        
        # Проверяем, что администратор не блокирует сам себя
        if phone_number == current_admin.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы не можете заблокировать свой собственный аккаунт"
            )
        
        # Проверяем существование пользователя
        user = get_user_by_phone_number(db, phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        # Обновляем статус блокировки
        updated_user = set_block_status(db, phone_number, is_blocked)
        
        if updated_user:
            return UserUpdateResponse(
                message=f"Пользователь {'заблокирован' if is_blocked else 'разблокирован'}",
                user=UserResponse.model_validate(updated_user)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении статуса блокировки"
            )
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error updating block status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении статуса блокировки"
        )


# ==================== Admin User Profile Management ====================

@router.patch("/user/name", response_model=UpdateResponse)
async def admin_update_user_name(
    request: AdminUpdateUserNameRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Обновление имени пользователя администратором
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    - **name**: новое имя пользователя
    """
    try:
        user = get_user_by_phone_number(db, request.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        user_extended = get_user_extended_by_id(db, user.id)
        if not user_extended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Расширенный профиль пользователя не найден"
            )
        
        updated_user = update_user_extended(
            db,
            user.id,
            UserExtendedUpdate(name=request.name)
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении имени"
            )
        
        return UpdateResponse(
            success=True,
            message="Имя пользователя успешно обновлено",
            data={"name": updated_user.name, "phone_number": request.phone_number}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error updating user name: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении имени пользователя"
        )


@router.patch("/user/balance", response_model=UpdateResponse)
async def admin_update_user_balance(
    request: AdminUpdateUserBalanceRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Обновление баланса пользователя администратором
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    - **balance**: новый баланс пользователя
    """
    try:
        user = get_user_by_phone_number(db, request.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        user_extended = get_user_extended_by_id(db, user.id)
        if not user_extended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Расширенный профиль пользователя не найден"
            )
        
        updated_user = update_user_extended(
            db,
            user.id,
            UserExtendedUpdate(balance=request.balance)
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении баланса"
            )
        
        balance_info = BalanceInfo.from_amount(updated_user.balance)
        
        return UpdateResponse(
            success=True,
            message="Баланс пользователя успешно обновлен",
            data={
                "balance": updated_user.balance,
                "balance_info": balance_info.model_dump(),
                "phone_number": request.phone_number
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error updating user balance: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении баланса пользователя"
        )


@router.patch("/user/rating", response_model=UpdateResponse)
async def admin_update_user_rating(
    request: AdminUpdateUserRatingRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Обновление рейтинга пользователя администратором
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    - **rating**: новый рейтинг пользователя (0-5)
    """
    try:
        user = get_user_by_phone_number(db, request.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        user_extended = get_user_extended_by_id(db, user.id)
        if not user_extended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Расширенный профиль пользователя не найден"
            )
        
        updated_user = update_user_extended(
            db,
            user.id,
            UserExtendedUpdate(rating=request.rating)
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении рейтинга"
            )
        
        return UpdateResponse(
            success=True,
            message="Рейтинг пользователя успешно обновлен",
            data={"rating": updated_user.rating, "phone_number": request.phone_number}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error updating user rating: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении рейтинга пользователя"
        )


@router.patch("/user/level", response_model=UpdateResponse)
async def admin_update_user_level(
    request: AdminUpdateUserLevelRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Обновление уровня пользователя администратором
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    - **level**: новый уровень пользователя (например: Новичок, Серебряный, Золотой, Платиновый)
    """
    try:
        user = get_user_by_phone_number(db, request.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        user_extended = get_user_extended_by_id(db, user.id)
        if not user_extended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Расширенный профиль пользователя не найден"
            )
        
        updated_user = update_user_extended(
            db,
            user.id,
            UserExtendedUpdate(level=request.level)
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении уровня"
            )
        
        return UpdateResponse(
            success=True,
            message="Уровень пользователя успешно обновлен",
            data={"level": updated_user.level, "phone_number": request.phone_number}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error updating user level: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении уровня пользователя"
        )


@router.patch("/user/documents", response_model=UpdateResponse)
async def admin_update_user_documents(
    request: AdminUpdateUserDocumentsRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Обновление статуса верификации документов пользователя администратором
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    - **passport_verified**: статус верификации паспорта (опционально)
    - **driving_license_verified**: статус верификации водительских прав (опционально)
    """
    try:
        user = get_user_by_phone_number(db, request.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        user_extended = get_user_extended_by_id(db, user.id)
        if not user_extended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Расширенный профиль пользователя не найден"
            )
        
        profile = get_profile_by_user_id(db, user_extended.id)
        if not profile:
            profile = create_profile(db, user_extended.id)
        
        # Подготавливаем данные для обновления
        update_data = {}
        if request.passport_verified is not None:
            update_data["passport_verified"] = request.passport_verified
        if request.driving_license_verified is not None:
            update_data["driving_license_verified"] = request.driving_license_verified
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо указать хотя бы одно поле для обновления"
            )
        
        updated_profile = update_profile(
            db,
            user_extended.id,
            UserProfileUpdate(**update_data)
        )
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении документов"
            )
        
        documents = ProfileDocuments(
            passport=DocumentInfo(
                image_url=updated_profile.passport_image_url,
                verified=updated_profile.passport_verified,
                uploaded_at=updated_profile.passport_uploaded_at
            ),
            driving_license=DocumentInfo(
                image_url=updated_profile.driving_license_image_url,
                verified=updated_profile.driving_license_verified,
                uploaded_at=updated_profile.driving_license_uploaded_at
            )
        )
        
        return UpdateResponse(
            success=True,
            message="Статус документов пользователя успешно обновлен",
            data={
                "documents": documents.model_dump(),
                "phone_number": request.phone_number
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error updating user documents: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении документов пользователя"
        )


def delete_file_by_url(file_url: str) -> bool:
    """
    Удаление файла по его URL
    
    Args:
        file_url: URL файла (например, http://localhost:8000/uploads/passports/1_abc123.jpg)
    
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


# ==================== Admin Document Verification ====================

@router.post("/user/documents/passport/approve", response_model=UpdateResponse)
async def admin_approve_passport(
    request: AdminVerifyDocumentRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Одобрение паспорта пользователя администратором
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    
    Устанавливает статус верификации паспорта в `true`.
    """
    try:
        user = get_user_by_phone_number(db, request.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        user_extended = get_user_extended_by_id(db, user.id)
        if not user_extended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Расширенный профиль пользователя не найден"
            )
        
        profile = get_profile_by_user_id(db, user_extended.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль пользователя не найден"
            )
        
        if not profile.passport_image_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У пользователя нет загруженного фото паспорта"
            )
        
        # Одобряем документ
        updated_profile = update_profile(
            db,
            user_extended.id,
            UserProfileUpdate(passport_verified=True)
        )
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении статуса паспорта"
            )
        
        documents = ProfileDocuments(
            passport=DocumentInfo(
                image_url=updated_profile.passport_image_url,
                verified=updated_profile.passport_verified,
                uploaded_at=updated_profile.passport_uploaded_at
            ),
            driving_license=DocumentInfo(
                image_url=updated_profile.driving_license_image_url,
                verified=updated_profile.driving_license_verified,
                uploaded_at=updated_profile.driving_license_uploaded_at
            )
        )
        
        return UpdateResponse(
            success=True,
            message="Паспорт пользователя одобрен",
            data={
                "documents": documents.model_dump(),
                "phone_number": request.phone_number
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error approving passport: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при одобрении паспорта"
        )


@router.post("/user/documents/passport/reject", response_model=UpdateResponse)
async def admin_reject_passport(
    request: AdminVerifyDocumentRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Отклонение паспорта пользователя администратором
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    
    Удаляет фото паспорта, сбрасывает статус верификации и дату загрузки.
    """
    try:
        user = get_user_by_phone_number(db, request.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        user_extended = get_user_extended_by_id(db, user.id)
        if not user_extended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Расширенный профиль пользователя не найден"
            )
        
        profile = get_profile_by_user_id(db, user_extended.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль пользователя не найден"
            )
        
        # Удаляем файл, если он существует
        if profile.passport_image_url:
            delete_file_by_url(profile.passport_image_url)
        
        # Сбрасываем данные паспорта
        updated_profile = update_profile(
            db,
            user_extended.id,
            UserProfileUpdate(
                passport_image_url=None,
                passport_verified=False,
                passport_uploaded_at=None
            )
        )
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при отклонении паспорта"
            )
        
        documents = ProfileDocuments(
            passport=DocumentInfo(
                image_url=None,
                verified=False,
                uploaded_at=None
            ),
            driving_license=DocumentInfo(
                image_url=updated_profile.driving_license_image_url,
                verified=updated_profile.driving_license_verified,
                uploaded_at=updated_profile.driving_license_uploaded_at
            )
        )
        
        return UpdateResponse(
            success=True,
            message="Паспорт пользователя отклонен, фото удалено",
            data={
                "documents": documents.model_dump(),
                "phone_number": request.phone_number
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error rejecting passport: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при отклонении паспорта"
        )


@router.post("/user/documents/driving-license/approve", response_model=UpdateResponse)
async def admin_approve_driving_license(
    request: AdminVerifyDocumentRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Одобрение водительских прав пользователя администратором
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    
    Устанавливает статус верификации водительских прав в `true`.
    """
    try:
        user = get_user_by_phone_number(db, request.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        user_extended = get_user_extended_by_id(db, user.id)
        if not user_extended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Расширенный профиль пользователя не найден"
            )
        
        profile = get_profile_by_user_id(db, user_extended.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль пользователя не найден"
            )
        
        if not profile.driving_license_image_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У пользователя нет загруженного фото водительских прав"
            )
        
        # Одобряем документ
        updated_profile = update_profile(
            db,
            user_extended.id,
            UserProfileUpdate(driving_license_verified=True)
        )
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении статуса водительских прав"
            )
        
        documents = ProfileDocuments(
            passport=DocumentInfo(
                image_url=updated_profile.passport_image_url,
                verified=updated_profile.passport_verified,
                uploaded_at=updated_profile.passport_uploaded_at
            ),
            driving_license=DocumentInfo(
                image_url=updated_profile.driving_license_image_url,
                verified=updated_profile.driving_license_verified,
                uploaded_at=updated_profile.driving_license_uploaded_at
            )
        )
        
        return UpdateResponse(
            success=True,
            message="Водительские права пользователя одобрены",
            data={
                "documents": documents.model_dump(),
                "phone_number": request.phone_number
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error approving driving license: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при одобрении водительских прав"
        )


@router.post("/user/documents/driving-license/reject", response_model=UpdateResponse)
async def admin_reject_driving_license(
    request: AdminVerifyDocumentRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Отклонение водительских прав пользователя администратором
    
    Требует прав администратора.
    - **phone_number**: номер телефона пользователя
    
    Удаляет фото водительских прав, сбрасывает статус верификации и дату загрузки.
    """
    try:
        user = get_user_by_phone_number(db, request.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        user_extended = get_user_extended_by_id(db, user.id)
        if not user_extended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Расширенный профиль пользователя не найден"
            )
        
        profile = get_profile_by_user_id(db, user_extended.id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль пользователя не найден"
            )
        
        # Удаляем файл, если он существует
        if profile.driving_license_image_url:
            delete_file_by_url(profile.driving_license_image_url)
        
        # Сбрасываем данные водительских прав
        updated_profile = update_profile(
            db,
            user_extended.id,
            UserProfileUpdate(
                driving_license_image_url=None,
                driving_license_verified=False,
                driving_license_uploaded_at=None
            )
        )
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при отклонении водительских прав"
            )
        
        documents = ProfileDocuments(
            passport=DocumentInfo(
                image_url=updated_profile.passport_image_url,
                verified=updated_profile.passport_verified,
                uploaded_at=updated_profile.passport_uploaded_at
            ),
            driving_license=DocumentInfo(
                image_url=None,
                verified=False,
                uploaded_at=None
            )
        )
        
        return UpdateResponse(
            success=True,
            message="Водительские права пользователя отклонены, фото удалено",
            data={
                "documents": documents.model_dump(),
                "phone_number": request.phone_number
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error rejecting driving license: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при отклонении водительских прав"
        )


# ==================== Admin Notifications Management ====================

@router.post("/notification", response_model=NotificationResponse)
async def create_notification_admin(
    notification: NotificationCreate,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Создание уведомления администратором
    
    Требует прав администратора.
    
    Типы уведомлений:
    - **Персональное**: укажите `user_id` - уведомление будет отправлено конкретному пользователю
    - **Глобальное**: не указывайте `user_id` (или укажите `null`) - уведомление будет отправлено всем пользователям
    
    Типы уведомлений (notification_type):
    - `info` - информационное уведомление
    - `warning` - предупреждение
    - `success` - успешное действие
    - `error` - ошибка
    - `promotion` - акция/промо
    """
    try:
        # Создаем уведомление в базе данных
        db_notification = create_notification(db, notification)
        
        # Отправляем через WebSocket
        notification_data = NotificationResponse.model_validate(db_notification).model_dump()
        
        if notification.user_id:
            # Персональное уведомление
            await notification_manager.send_personal_notification(
                notification.user_id,
                {
                    "type": "notification",
                    "notification": notification_data
                }
            )
        else:
            # Глобальное уведомление
            await notification_manager.send_global_notification({
                "type": "notification",
                "notification": notification_data
            })
        
        return NotificationResponse.model_validate(db_notification)
        
    except Exception as e:
        import traceback
        print(f"Error creating notification: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании уведомления"
        )


@router.get("/notifications", response_model=NotificationListResponse)
async def get_all_notifications_admin(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    user_id: Optional[int] = Query(None, description="Фильтр по пользователю"),
    notification_type: Optional[str] = Query(None, description="Фильтр по типу уведомления")
):
    """
    Получение списка всех уведомлений (для администратора)
    
    Доступно только администраторам.
    Поддерживает фильтрацию по пользователю и типу уведомления.
    """
    try:
        notifications, total = get_all_notifications(
            db,
            skip=skip,
            limit=limit,
            user_id=user_id,
            notification_type=notification_type
        )
        
        return NotificationListResponse(
            notifications=[NotificationResponse.model_validate(n) for n in notifications],
            total=total,
            unread_count=0,  # Для администратора не считаем непрочитанные
            skip=skip,
            limit=limit
        )
    except Exception as e:
        import traceback
        print(f"Error getting notifications: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка уведомлений"
        )


@router.delete("/notification/{notification_id}", response_model=dict)
async def delete_notification_by_admin(
    notification_id: int,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Удаление уведомления администратором
    
    Доступно только администраторам.
    Удаляет уведомление полностью из БД, включая все связанные записи.
    Можно удалять как персональные, так и глобальные уведомления.
    """
    deleted = delete_notification_admin(db, notification_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Уведомление не найдено"
        )
    
    return {
        "success": True,
        "message": "Уведомление успешно удалено",
        "notification_id": notification_id
    }

