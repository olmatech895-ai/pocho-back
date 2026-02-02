"""
CRUD операции для Favorites Service
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user_extended import UserFavorite
from app.schemas.user_extended import UserFavoriteCreate


def get_favorites_by_user_id(
    db: Session,
    user_id: int,
    favorite_type: Optional[str] = None
) -> List[UserFavorite]:
    """Получение избранного пользователя"""
    query = db.query(UserFavorite).filter(UserFavorite.user_id == user_id)
    
    if favorite_type:
        query = query.filter(UserFavorite.favorite_type == favorite_type)
    
    return query.order_by(UserFavorite.added_at.desc()).all()


def get_favorite_by_place(
    db: Session,
    user_id: int,
    favorite_type: str,
    place_id: int
) -> Optional[UserFavorite]:
    """Получение конкретного избранного"""
    return db.query(UserFavorite).filter(
        and_(
            UserFavorite.user_id == user_id,
            UserFavorite.favorite_type == favorite_type,
            UserFavorite.place_id == place_id
        )
    ).first()


def create_favorite(
    db: Session,
    user_id: int,
    favorite: UserFavoriteCreate
) -> UserFavorite:
    """Создание избранного"""
    # Проверяем, не существует ли уже
    existing = get_favorite_by_place(db, user_id, favorite.favorite_type, favorite.place_id)
    if existing:
        return existing
    
    db_favorite = UserFavorite(
        user_id=user_id,
        favorite_type=favorite.favorite_type,
        place_id=favorite.place_id,
        extra_data=favorite.extra_data
    )
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite


def delete_favorite(
    db: Session,
    user_id: int,
    favorite_type: str,
    place_id: int
) -> bool:
    """Удаление избранного"""
    favorite = get_favorite_by_place(db, user_id, favorite_type, place_id)
    if not favorite:
        return False
    
    db.delete(favorite)
    db.commit()
    return True


def get_favorites_count_by_type(db: Session, user_id: int, favorite_type: str) -> int:
    """Получение количества избранного по типу"""
    return db.query(UserFavorite).filter(
        and_(
            UserFavorite.user_id == user_id,
            UserFavorite.favorite_type == favorite_type
        )
    ).count()

