"""
CRUD операции для Statistics Service
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user_extended import UserStatistics
from app.services.favorites_service.crud import get_favorites_count_by_type


def get_statistics_by_user_id(db: Session, user_id: int) -> Optional[UserStatistics]:
    """Получение статистики пользователя"""
    return db.query(UserStatistics).filter(UserStatistics.user_id == user_id).first()


def create_statistics(db: Session, user_id: int) -> UserStatistics:
    """Создание статистики пользователя"""
    db_statistics = UserStatistics(user_id=user_id)
    db.add(db_statistics)
    db.commit()
    db.refresh(db_statistics)
    return db_statistics


def update_statistics_from_favorites(db: Session, user_id: int) -> Optional[UserStatistics]:
    """Обновление статистики на основе избранного"""
    statistics = get_statistics_by_user_id(db, user_id)
    if not statistics:
        statistics = create_statistics(db, user_id)
    
    # Обновляем счетчики избранного
    statistics.favorite_fuel_stations_count = get_favorites_count_by_type(
        db, user_id, "fuel_station"
    )
    statistics.favorite_restaurants_count = get_favorites_count_by_type(
        db, user_id, "restaurant"
    )
    statistics.favorite_car_services_count = get_favorites_count_by_type(
        db, user_id, "car_service"
    )
    statistics.favorite_car_washes_count = get_favorites_count_by_type(
        db, user_id, "car_wash"
    )
    statistics.favorite_charging_stations_count = get_favorites_count_by_type(
        db, user_id, "charging_station"
    )
    
    statistics.total_favorites_count = (
        statistics.favorite_fuel_stations_count +
        statistics.favorite_restaurants_count +
        statistics.favorite_car_services_count +
        statistics.favorite_car_washes_count +
        statistics.favorite_charging_stations_count
    )
    
    db.commit()
    db.refresh(statistics)
    return statistics


def update_statistics(
    db: Session,
    user_id: int,
    total_spent: Optional[float] = None,
    average_rating_given: Optional[float] = None,
    reviews_written: Optional[int] = None
) -> Optional[UserStatistics]:
    """Обновление статистики"""
    statistics = get_statistics_by_user_id(db, user_id)
    if not statistics:
        statistics = create_statistics(db, user_id)
    
    if total_spent is not None:
        statistics.total_spent = total_spent
    if average_rating_given is not None:
        statistics.average_rating_given = average_rating_given
    if reviews_written is not None:
        statistics.reviews_written = reviews_written
    
    db.commit()
    db.refresh(statistics)
    return statistics

