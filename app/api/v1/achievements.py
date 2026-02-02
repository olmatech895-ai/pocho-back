"""
API эндпоинты для достижений пользователя
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.achievements_service.crud import (
    get_achievements_by_user_id,
    get_achievement_by_type,
    create_achievement,
    unlock_achievement,
    update_achievement,
)
from app.services.user_service.crud import get_user_extended_by_id, create_user_extended
from app.schemas.user_extended import (
    UserAchievementResponse,
    UserAchievementUpdate,
    UserAchievementCreate,
    UserExtendedCreate,
)

router = APIRouter()


@router.get("", response_model=list[UserAchievementResponse])
async def get_user_achievements(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    unlocked_only: Optional[bool] = Query(None, description="Только разблокированные (true) или только заблокированные (false)")
):
    """
    Получение всех достижений пользователя
    
    Возвращает список достижений пользователя из отдельной таблицы user_achievements.
    Каждое достижение содержит:
    - achievement_type: тип достижения (например: "first_refuel", "star_driver", "lover", "premium")
    - unlocked: статус (true - разблокировано, false - заблокировано)
    - Метаданные: icon, title, description, color
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
            from app.services.user_service.crud import create_user_extended
            user_extended = create_user_extended(db, user_extended_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при создании расширенного профиля"
            )
    
    achievements = get_achievements_by_user_id(db, user_extended.id, unlocked_only)
    return [UserAchievementResponse.model_validate(a) for a in achievements]


@router.get("/{achievement_type}", response_model=UserAchievementResponse)
async def get_user_achievement(
    achievement_type: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение конкретного достижения пользователя по типу"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    achievement = get_achievement_by_type(db, user_extended.id, achievement_type)
    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Достижение типа '{achievement_type}' не найдено"
        )
    
    return UserAchievementResponse.model_validate(achievement)


@router.post("", response_model=UserAchievementResponse)
async def create_user_achievement(
    achievement_create: UserAchievementCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание нового достижения для пользователя"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    achievement = create_achievement(db, user_extended.id, achievement_create)
    return UserAchievementResponse.model_validate(achievement)


@router.post("/{achievement_type}/unlock", response_model=UserAchievementResponse)
async def unlock_user_achievement(
    achievement_type: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Разблокировка достижения по типу"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    achievement = unlock_achievement(db, user_extended.id, achievement_type)
    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Достижение типа '{achievement_type}' не найдено"
        )
    
    return UserAchievementResponse.model_validate(achievement)


@router.patch("/{achievement_type}", response_model=UserAchievementResponse)
async def update_user_achievement(
    achievement_type: str,
    achievement_update: UserAchievementUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление достижения пользователя"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    achievement = update_achievement(db, user_extended.id, achievement_type, achievement_update)
    if not achievement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Достижение типа '{achievement_type}' не найдено"
        )
    
    return UserAchievementResponse.model_validate(achievement)

