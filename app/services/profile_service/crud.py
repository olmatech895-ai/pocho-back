"""
CRUD операции для Profile Service
"""
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.user_extended import UserProfile
from app.schemas.user_extended import UserProfileUpdate


def get_profile_by_user_id(db: Session, user_id: int) -> Optional[UserProfile]:
    """Получение профиля по user_id"""
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def create_profile(db: Session, user_id: int) -> UserProfile:
    """
    Создание профиля пользователя с настройками по умолчанию
    
    Устанавливает:
    - Документы: passport и driving_license с verified=False, image_url=None, uploaded_at=None
    - Настройки: notifications_enabled=True, language="ru"
    """
    db_profile = UserProfile(
        user_id=user_id,
        # Документы по умолчанию - все None/False
        passport_image_url=None,
        passport_verified=False,
        passport_uploaded_at=None,
        driving_license_image_url=None,
        driving_license_verified=False,
        driving_license_uploaded_at=None,
        # Настройки по умолчанию
        settings={"notifications_enabled": True, "language": "ru"}
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def update_profile(
    db: Session,
    user_id: int,
    profile_update: UserProfileUpdate
) -> Optional[UserProfile]:
    """Обновление профиля пользователя"""
    profile = get_profile_by_user_id(db, user_id)
    if not profile:
        return None
    
    update_data = profile_update.model_dump(exclude_unset=True)
    
    # Обновление паспорта
    if "passport_image_url" in update_data:
        profile.passport_image_url = update_data["passport_image_url"]
        if update_data["passport_image_url"]:
            profile.passport_uploaded_at = datetime.now(timezone.utc)
        else:
            # Если image_url установлен в None, сбрасываем и uploaded_at
            profile.passport_uploaded_at = None
    
    if "passport_verified" in update_data:
        profile.passport_verified = update_data["passport_verified"]
    
    if "passport_uploaded_at" in update_data:
        profile.passport_uploaded_at = update_data["passport_uploaded_at"]
    
    # Обновление водительских прав
    if "driving_license_image_url" in update_data:
        profile.driving_license_image_url = update_data["driving_license_image_url"]
        if update_data["driving_license_image_url"]:
            profile.driving_license_uploaded_at = datetime.now(timezone.utc)
        else:
            # Если image_url установлен в None, сбрасываем и uploaded_at
            profile.driving_license_uploaded_at = None
    
    if "driving_license_verified" in update_data:
        profile.driving_license_verified = update_data["driving_license_verified"]
    
    if "driving_license_uploaded_at" in update_data:
        profile.driving_license_uploaded_at = update_data["driving_license_uploaded_at"]
    
    # Обновление настроек
    if "settings" in update_data:
        if profile.settings:
            profile.settings.update(update_data["settings"])
        else:
            profile.settings = update_data["settings"]
    
    db.commit()
    db.refresh(profile)
    return profile

