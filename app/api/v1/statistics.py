"""
API эндпоинты для статистики
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.statistics_service.crud import (
    get_statistics_by_user_id,
    create_statistics,
    update_statistics_from_favorites,
)
from app.services.user_service.crud import get_user_extended_by_id
from app.schemas.user_extended import UserStatisticsResponse

router = APIRouter()


@router.get("", response_model=UserStatisticsResponse)
async def get_statistics(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение статистики пользователя"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    statistics = get_statistics_by_user_id(db, user_extended.id)
    if not statistics:
        statistics = create_statistics(db, user_extended.id)
    
    # Обновляем статистику из избранного
    statistics = update_statistics_from_favorites(db, user_extended.id)
    
    return UserStatisticsResponse.model_validate(statistics)

