"""
CRUD операции для Electric Station Service
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from math import radians, cos, sin, asin, sqrt

from app.models.electric_station import (
    ElectricStation,
    ChargingPoint,
    ElectricStationPhoto,
    ElectricStationReview,
    ConnectorType,
    ElectricStationStatus,
    ChargingPointStatus,
)
from app.schemas.electric_station import (
    ElectricStationCreate,
    ElectricStationUpdate,
    ChargingPointCreate,
    ChargingPointUpdate,
    ElectricStationFilter,
    ElectricStationReviewCreate,
    ElectricStationReviewUpdate,
)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Вычисляет расстояние между двумя точками на Земле в километрах
    используя формулу гаверсинуса
    """
    R = 6371  # Радиус Земли в километрах
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    
    return R * c


# ==================== Electric Station CRUD ====================

def create_electric_station(
    db: Session,
    station_data: ElectricStationCreate,
    created_by_user_id: Optional[int] = None,
    created_by_admin_id: Optional[int] = None
) -> ElectricStation:
    """Создание электрозаправки"""
    station_dict = station_data.model_dump(exclude={"charging_points"})
    station_dict["created_by_user_id"] = created_by_user_id
    station_dict["created_by_admin_id"] = created_by_admin_id
    
    # Если создает админ, сразу одобряем
    if created_by_admin_id:
        station_dict["status"] = ElectricStationStatus.APPROVED
    
    db_station = ElectricStation(**station_dict)
    db.add(db_station)
    db.flush()  # Получаем ID станции
    
    # Добавляем зарядные точки
    total_points = 0
    available_points = 0
    if station_data.charging_points:
        for point_data in station_data.charging_points:
            charging_point = ChargingPoint(
                electric_station_id=db_station.id,
                connector_type=point_data.connector_type.value,
                power_kw=point_data.power_kw,
                connector_name=point_data.connector_name,
                price_per_kwh=point_data.price_per_kwh,
                price_per_minute=point_data.price_per_minute,
                min_price=point_data.min_price,
                status=point_data.status.value
            )
            db.add(charging_point)
            total_points += 1
            if point_data.status == ChargingPointStatus.AVAILABLE:
                available_points += 1
    
    # Обновляем счетчики точек
    db_station.total_points = total_points
    db_station.available_points = available_points
    
    db.commit()
    db.refresh(db_station)
    return db_station


def get_electric_station_by_id(db: Session, station_id: int) -> Optional[ElectricStation]:
    """Получение электрозаправки по ID"""
    return db.query(ElectricStation).filter(ElectricStation.id == station_id).first()


def get_electric_stations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[ElectricStationFilter] = None
) -> Tuple[List[ElectricStation], int]:
    """Получение списка электрозаправок с фильтрацией"""
    query = db.query(ElectricStation)
    
    # Фильтр по статусу (по умолчанию только одобренные)
    if filters and filters.status:
        query = query.filter(ElectricStation.status == filters.status.value)
    else:
        query = query.filter(ElectricStation.status == ElectricStationStatus.APPROVED)
    
    # Фильтр по типу разъема (через зарядные точки)
    charging_point_joined = False
    if filters and filters.connector_type:
        try:
            connector_type_enum = ConnectorType(filters.connector_type)
            query = query.join(ChargingPoint).filter(
                ChargingPoint.connector_type == connector_type_enum
            )
            charging_point_joined = True
            if filters.min_power_kw:
                query = query.filter(ChargingPoint.power_kw >= filters.min_power_kw)
            if filters.max_power_kw:
                query = query.filter(ChargingPoint.power_kw <= filters.max_power_kw)
            if filters.min_price_per_kwh:
                query = query.filter(
                    or_(
                        ChargingPoint.price_per_kwh.is_(None),
                        ChargingPoint.price_per_kwh >= filters.min_price_per_kwh
                    )
                )
            if filters.max_price_per_kwh:
                query = query.filter(
                    or_(
                        ChargingPoint.price_per_kwh.is_(None),
                        ChargingPoint.price_per_kwh <= filters.max_price_per_kwh
                    )
                )
        except ValueError:
            pass
    elif filters and (filters.min_power_kw or filters.max_power_kw or filters.min_price_per_kwh or filters.max_price_per_kwh):
        query = query.join(ChargingPoint)
        charging_point_joined = True
        if filters.min_power_kw:
            query = query.filter(ChargingPoint.power_kw >= filters.min_power_kw)
        if filters.max_power_kw:
            query = query.filter(ChargingPoint.power_kw <= filters.max_power_kw)
        if filters.min_price_per_kwh:
            query = query.filter(
                or_(
                    ChargingPoint.price_per_kwh.is_(None),
                    ChargingPoint.price_per_kwh >= filters.min_price_per_kwh
                )
            )
        if filters.max_price_per_kwh:
            query = query.filter(
                or_(
                    ChargingPoint.price_per_kwh.is_(None),
                    ChargingPoint.price_per_kwh <= filters.max_price_per_kwh
                )
            )
    
    # Фильтр по минимальному рейтингу
    if filters and filters.min_rating is not None:
        query = query.filter(ElectricStation.rating >= filters.min_rating)
    
    # Фильтр по режиму работы
    if filters and filters.is_24_7 is not None:
        query = query.filter(ElectricStation.is_24_7 == filters.is_24_7)
    
    # Фильтр по наличию акций
    if filters and filters.has_promotions is not None:
        query = query.filter(ElectricStation.has_promotions == filters.has_promotions)
    
    # Фильтр по дополнительным услугам
    if filters and filters.has_parking is not None:
        query = query.filter(ElectricStation.has_parking == filters.has_parking)
    if filters and filters.has_waiting_room is not None:
        query = query.filter(ElectricStation.has_waiting_room == filters.has_waiting_room)
    if filters and filters.has_cafe is not None:
        query = query.filter(ElectricStation.has_cafe == filters.has_cafe)
    if filters and filters.has_restroom is not None:
        query = query.filter(ElectricStation.has_restroom == filters.has_restroom)
    if filters and filters.accepts_cards is not None:
        query = query.filter(ElectricStation.accepts_cards == filters.accepts_cards)
    if filters and filters.has_mobile_app is not None:
        query = query.filter(ElectricStation.has_mobile_app == filters.has_mobile_app)
    if filters and filters.requires_membership is not None:
        query = query.filter(ElectricStation.requires_membership == filters.requires_membership)
    
    # Фильтр по наличию свободных точек
    if filters and filters.has_available_points is not None:
        if filters.has_available_points:
            query = query.filter(ElectricStation.available_points > 0)
        else:
            query = query.filter(ElectricStation.available_points == 0)
    
    # Фильтр по оператору
    if filters and filters.operator:
        query = query.filter(ElectricStation.operator.ilike(f"%{filters.operator}%"))
    
    # Фильтр по сети
    if filters and filters.network:
        query = query.filter(ElectricStation.network.ilike(f"%{filters.network}%"))
    
    # Поиск по названию или адресу
    if filters and filters.search_query:
        search_term = f"%{filters.search_query}%"
        query = query.filter(
            or_(
                ElectricStation.name.ilike(search_term),
                ElectricStation.address.ilike(search_term),
                ElectricStation.description.ilike(search_term)
            )
        )
    
    # Поиск по близости
    if filters and filters.latitude and filters.longitude and filters.radius_km:
        all_stations = query.all()
        filtered_stations = []
        for station in all_stations:
            distance = haversine_distance(
                filters.latitude,
                filters.longitude,
                station.latitude,
                station.longitude
            )
            if distance <= filters.radius_km:
                filtered_stations.append(station)
        
        total = len(filtered_stations)
        stations = filtered_stations[skip:skip + limit]
        return stations, total
    
    # Подсчет общего количества
    total = query.count()
    
    # Применяем пагинацию
    stations = query.order_by(ElectricStation.rating.desc(), ElectricStation.reviews_count.desc()).offset(skip).limit(limit).all()
    
    return stations, total


def update_electric_station(
    db: Session,
    station_id: int,
    station_update: ElectricStationUpdate
) -> Optional[ElectricStation]:
    """Обновление электрозаправки"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        return None
    
    update_data = station_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(station, field, value)
    
    db.commit()
    db.refresh(station)
    return station


def delete_electric_station(db: Session, station_id: int) -> bool:
    """Удаление электрозаправки"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        return False
    
    db.delete(station)
    db.commit()
    return True


def approve_electric_station(db: Session, station_id: int) -> Optional[ElectricStation]:
    """Одобрение электрозаправки"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        return None
    
    station.status = ElectricStationStatus.APPROVED
    station.approved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(station)
    return station


def reject_electric_station(db: Session, station_id: int) -> Optional[ElectricStation]:
    """Отклонение электрозаправки"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        return None
    
    station.status = ElectricStationStatus.REJECTED
    
    db.commit()
    db.refresh(station)
    return station


# ==================== Charging Point CRUD ====================

def create_or_update_charging_point(
    db: Session,
    station_id: int,
    point_data: ChargingPointCreate
) -> ChargingPoint:
    """Создание или обновление зарядной точки"""
    charging_point = ChargingPoint(
        electric_station_id=station_id,
        connector_type=point_data.connector_type.value,
        power_kw=point_data.power_kw,
        connector_name=point_data.connector_name,
        price_per_kwh=point_data.price_per_kwh,
        price_per_minute=point_data.price_per_minute,
        min_price=point_data.min_price,
        status=point_data.status.value
    )
    db.add(charging_point)
    db.flush()
    
    # Обновляем счетчики станции
    _update_station_points_counters(db, station_id)
    
    db.commit()
    db.refresh(charging_point)
    return charging_point


def update_charging_point(
    db: Session,
    point_id: int,
    point_update: ChargingPointUpdate
) -> Optional[ChargingPoint]:
    """Обновление зарядной точки"""
    charging_point = db.query(ChargingPoint).filter(ChargingPoint.id == point_id).first()
    if not charging_point:
        return None
    
    update_data = point_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "connector_type" and value:
            setattr(charging_point, field, value.value)
        elif field == "status" and value:
            setattr(charging_point, field, value.value)
        else:
            setattr(charging_point, field, value)
    
    db.commit()
    db.refresh(charging_point)
    
    # Обновляем счетчики станции
    _update_station_points_counters(db, charging_point.electric_station_id)
    
    return charging_point


def bulk_update_charging_points(
    db: Session,
    station_id: int,
    points: List[ChargingPointCreate]
) -> List[ChargingPoint]:
    """Массовое обновление зарядных точек"""
    # Удаляем старые точки
    db.query(ChargingPoint).filter(ChargingPoint.electric_station_id == station_id).delete()
    
    # Создаем новые точки
    updated_points = []
    for point_data in points:
        point = create_or_update_charging_point(db, station_id, point_data)
        updated_points.append(point)
    
    return updated_points


def get_charging_points_by_station(db: Session, station_id: int) -> List[ChargingPoint]:
    """Получение всех зарядных точек станции"""
    return db.query(ChargingPoint).filter(
        ChargingPoint.electric_station_id == station_id
    ).order_by(ChargingPoint.connector_type, ChargingPoint.created_at).all()


def delete_charging_point(db: Session, point_id: int) -> bool:
    """Удаление зарядной точки"""
    charging_point = db.query(ChargingPoint).filter(ChargingPoint.id == point_id).first()
    if not charging_point:
        return False
    
    station_id = charging_point.electric_station_id
    db.delete(charging_point)
    db.commit()
    
    # Обновляем счетчики станции
    _update_station_points_counters(db, station_id)
    
    return True


def _update_station_points_counters(db: Session, station_id: int):
    """Обновление счетчиков зарядных точек станции"""
    station = get_electric_station_by_id(db, station_id)
    if station:
        total_points = db.query(ChargingPoint).filter(
            ChargingPoint.electric_station_id == station_id
        ).count()
        available_points = db.query(ChargingPoint).filter(
            and_(
                ChargingPoint.electric_station_id == station_id,
                ChargingPoint.status == ChargingPointStatus.AVAILABLE
            )
        ).count()
        
        station.total_points = total_points
        station.available_points = available_points
        db.commit()


# ==================== Photo CRUD ====================

def add_electric_station_photo(
    db: Session,
    station_id: int,
    photo_url: str,
    is_main: bool = False,
    order: int = 0,
    uploaded_by_user_id: Optional[int] = None,
    uploaded_by_admin_id: Optional[int] = None
) -> ElectricStationPhoto:
    """Добавление фотографии к электрозаправке"""
    # Если это главная фотография, снимаем флаг с других
    if is_main:
        db.query(ElectricStationPhoto).filter(
            ElectricStationPhoto.electric_station_id == station_id,
            ElectricStationPhoto.is_main == True
        ).update({"is_main": False})
    
    photo = ElectricStationPhoto(
        electric_station_id=station_id,
        photo_url=photo_url,
        is_main=is_main,
        order=order,
        uploaded_by_user_id=uploaded_by_user_id,
        uploaded_by_admin_id=uploaded_by_admin_id
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def get_electric_station_photos(db: Session, station_id: int) -> List[ElectricStationPhoto]:
    """Получение всех фотографий электрозаправки"""
    return db.query(ElectricStationPhoto).filter(
        ElectricStationPhoto.electric_station_id == station_id
    ).order_by(ElectricStationPhoto.is_main.desc(), ElectricStationPhoto.order, ElectricStationPhoto.created_at).all()


def delete_electric_station_photo(db: Session, photo_id: int) -> bool:
    """Удаление фотографии"""
    photo = db.query(ElectricStationPhoto).filter(ElectricStationPhoto.id == photo_id).first()
    if not photo:
        return False
    
    db.delete(photo)
    db.commit()
    return True


def set_main_photo(db: Session, station_id: int, photo_id: int) -> Optional[ElectricStationPhoto]:
    """Установка главной фотографии"""
    photo = db.query(ElectricStationPhoto).filter(
        and_(
            ElectricStationPhoto.id == photo_id,
            ElectricStationPhoto.electric_station_id == station_id
        )
    ).first()
    if not photo:
        return None
    
    # Снимаем флаг с других фотографий
    db.query(ElectricStationPhoto).filter(
        and_(
            ElectricStationPhoto.electric_station_id == station_id,
            ElectricStationPhoto.is_main == True
        )
    ).update({"is_main": False})
    
    photo.is_main = True
    db.commit()
    db.refresh(photo)
    return photo


# ==================== Review CRUD ====================

def create_review(
    db: Session,
    station_id: int,
    user_id: int,
    review_data: ElectricStationReviewCreate
) -> ElectricStationReview:
    """Создание отзыва"""
    # Проверяем, есть ли уже отзыв от этого пользователя
    existing_review = db.query(ElectricStationReview).filter(
        and_(
            ElectricStationReview.electric_station_id == station_id,
            ElectricStationReview.user_id == user_id
        )
    ).first()
    
    if existing_review:
        # Обновляем существующий отзыв
        existing_review.rating = review_data.rating
        existing_review.comment = review_data.comment
        existing_review.charging_speed_rating = review_data.charging_speed_rating
        existing_review.price_rating = review_data.price_rating
        existing_review.location_rating = review_data.location_rating
        db.commit()
        db.refresh(existing_review)
        review = existing_review
    else:
        # Создаем новый отзыв
        review = ElectricStationReview(
            electric_station_id=station_id,
            user_id=user_id,
            rating=review_data.rating,
            comment=review_data.comment,
            charging_speed_rating=review_data.charging_speed_rating,
            price_rating=review_data.price_rating,
            location_rating=review_data.location_rating
        )
        db.add(review)
        db.commit()
        db.refresh(review)
    
    # Пересчитываем рейтинг станции
    _recalculate_station_rating(db, station_id)
    
    return review


def get_reviews_by_station(
    db: Session,
    station_id: int,
    skip: int = 0,
    limit: int = 50
) -> Tuple[List[ElectricStationReview], int]:
    """Получение отзывов по электрозаправке"""
    query = db.query(ElectricStationReview).filter(ElectricStationReview.electric_station_id == station_id)
    total = query.count()
    reviews = query.order_by(ElectricStationReview.created_at.desc()).offset(skip).limit(limit).all()
    return reviews, total


def update_review(
    db: Session,
    review_id: int,
    user_id: int,
    review_update: ElectricStationReviewUpdate
) -> Optional[ElectricStationReview]:
    """Обновление отзыва"""
    review = db.query(ElectricStationReview).filter(
        and_(
            ElectricStationReview.id == review_id,
            ElectricStationReview.user_id == user_id
        )
    ).first()
    if not review:
        return None
    
    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)
    
    db.commit()
    db.refresh(review)
    
    # Пересчитываем рейтинг станции
    _recalculate_station_rating(db, review.electric_station_id)
    
    return review


def delete_review(db: Session, review_id: int, user_id: int) -> bool:
    """Удаление отзыва"""
    review = db.query(ElectricStationReview).filter(
        and_(
            ElectricStationReview.id == review_id,
            ElectricStationReview.user_id == user_id
        )
    ).first()
    if not review:
        return False
    
    station_id = review.electric_station_id
    db.delete(review)
    db.commit()
    
    # Пересчитываем рейтинг станции
    _recalculate_station_rating(db, station_id)
    
    return True


def _recalculate_station_rating(db: Session, station_id: int):
    """Пересчет рейтинга электрозаправки на основе отзывов"""
    reviews = db.query(ElectricStationReview).filter(ElectricStationReview.electric_station_id == station_id).all()
    
    if not reviews:
        rating = 0.0
        count = 0
    else:
        rating = sum(r.rating for r in reviews) / len(reviews)
        count = len(reviews)
    
    station = get_electric_station_by_id(db, station_id)
    if station:
        station.rating = round(rating, 2)
        station.reviews_count = count
        db.commit()










