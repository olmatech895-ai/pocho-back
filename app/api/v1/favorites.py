"""
API эндпоинты для избранного
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.favorites_service.crud import (
    get_favorites_by_user_id,
    create_favorite,
    delete_favorite,
    get_favorite_by_place,
)
from app.services.user_service.crud import get_user_extended_by_id
from app.schemas.user_extended import (
    UserFavoriteCreate,
    UserFavoriteResponse,
    FavoritesListResponse,
)

router = APIRouter()


@router.get("", response_model=FavoritesListResponse)
async def get_favorites(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    favorite_type: Optional[str] = Query(None, description="Тип избранного")
):
    """Получение избранного пользователя"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    favorites_all = get_favorites_by_user_id(db, user_extended.id, favorite_type)
    
    # Маппинг favorite_type (ед.ч.) -> ключ в ответе (мн.ч.)
    _TYPE_TO_KEY = {
        "fuel_station": "fuel_stations",
        "restaurant": "restaurants",
        "car_service": "car_services",
        "car_wash": "car_washes",
        "charging_station": "charging_stations",
    }

    if favorite_type:
        # Если указан тип, возвращаем только его
        key = _TYPE_TO_KEY.get(favorite_type, favorite_type)
        return FavoritesListResponse(**{key: favorites_all})
    
    # Группируем по типам
    favorites_dict = {
        "fuel_stations": [],
        "restaurants": [],
        "car_services": [],
        "car_washes": [],
        "charging_stations": [],
    }
    
    for fav in favorites_all:
        key = _TYPE_TO_KEY.get(fav.favorite_type)
        if key and key in favorites_dict:
            favorites_dict[key].append(fav)
    
    return FavoritesListResponse(**favorites_dict)


@router.post("", response_model=UserFavoriteResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    favorite: UserFavoriteCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Добавление в избранное"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    # Проверяем валидность типа
    valid_types = ["fuel_station", "restaurant", "car_service", "car_wash", "charging_station"]
    if favorite.favorite_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный тип избранного. Допустимые: {', '.join(valid_types)}"
        )
    
    created_favorite = create_favorite(db, user_extended.id, favorite)
    return UserFavoriteResponse.model_validate(created_favorite)


@router.delete("/{favorite_type}/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    favorite_type: str,
    place_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление из избранного"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    deleted = delete_favorite(db, user_extended.id, favorite_type, place_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Избранное не найдено"
        )


@router.get("/check/{favorite_type}/{place_id}", response_model=dict)
async def check_favorite(
    favorite_type: str,
    place_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Проверка, находится ли место в избранном"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    favorite = get_favorite_by_place(db, user_extended.id, favorite_type, place_id)
    return {"is_favorite": favorite is not None}

