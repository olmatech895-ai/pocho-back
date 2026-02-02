"""
CRUD операции для Achievements Service
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.user_extended import UserAchievement
from app.schemas.user_extended import UserAchievementUpdate, UserAchievementCreate


def get_achievements_by_user_id(
    db: Session,
    user_id: int,
    unlocked_only: Optional[bool] = None
) -> List[UserAchievement]:
    """
    Получение всех достижений пользователя
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя (из users_extended)
        unlocked_only: Если True - только разблокированные, если False - только заблокированные, если None - все
    
    Returns:
        Список достижений пользователя
    """
    query = db.query(UserAchievement).filter(UserAchievement.user_id == user_id)
    
    if unlocked_only is not None:
        query = query.filter(UserAchievement.unlocked == unlocked_only)
    
    return query.order_by(UserAchievement.created_at.desc()).all()


def get_achievement_by_type(
    db: Session,
    user_id: int,
    achievement_type: str
) -> Optional[UserAchievement]:
    """Получение конкретного достижения по типу"""
    return db.query(UserAchievement).filter(
        UserAchievement.user_id == user_id,
        UserAchievement.achievement_type == achievement_type
    ).first()


def create_achievement(
    db: Session,
    user_id: int,
    achievement_create: UserAchievementCreate
) -> UserAchievement:
    """
    Создание достижения для пользователя
    
    Если достижение с таким типом уже существует - возвращает существующее
    """
    # Проверяем, не существует ли уже
    existing = get_achievement_by_type(db, user_id, achievement_create.achievement_type)
    if existing:
        return existing
    
    db_achievement = UserAchievement(
        user_id=user_id,
        achievement_type=achievement_create.achievement_type,
        icon=achievement_create.icon,
        title=achievement_create.title,
        description=achievement_create.description,
        color=achievement_create.color,
        unlocked=False
    )
    db.add(db_achievement)
    db.commit()
    db.refresh(db_achievement)
    return db_achievement


def unlock_achievement(
    db: Session,
    user_id: int,
    achievement_type: str
) -> Optional[UserAchievement]:
    """Разблокировка достижения по типу"""
    achievement = get_achievement_by_type(db, user_id, achievement_type)
    if not achievement:
        return None
    
    achievement.unlocked = True
    achievement.unlocked_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(achievement)
    return achievement


def update_achievement(
    db: Session,
    user_id: int,
    achievement_type: str,
    achievement_update: UserAchievementUpdate
) -> Optional[UserAchievement]:
    """Обновление достижения"""
    achievement = get_achievement_by_type(db, user_id, achievement_type)
    if not achievement:
        return None
    
    # Обновляем статус разблокировки
    if achievement_update.unlocked is not None:
        achievement.unlocked = achievement_update.unlocked
        if achievement_update.unlocked and not achievement.unlocked_at:
            achievement.unlocked_at = datetime.now(timezone.utc)
        elif not achievement_update.unlocked:
            achievement.unlocked_at = None
    
    if achievement_update.unlocked_at:
        achievement.unlocked_at = achievement_update.unlocked_at
    
    # Обновляем метаданные
    if achievement_update.icon is not None:
        achievement.icon = achievement_update.icon
    if achievement_update.title is not None:
        achievement.title = achievement_update.title
    if achievement_update.description is not None:
        achievement.description = achievement_update.description
    if achievement_update.color is not None:
        achievement.color = achievement_update.color
    
    db.commit()
    db.refresh(achievement)
    return achievement

