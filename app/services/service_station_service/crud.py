"""
CRUD операции для Service Station Service
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from math import radians, cos, sin, asin, sqrt

from app.models.service_station import (
    ServiceStation,
    ServicePrice,
    ServiceStationPhoto,
    ServiceStationReview,
    ServiceType,
    ServiceStationStatus,
)
from app.schemas.service_station import (
    ServiceStationCreate,
    ServiceStationUpdate,
    ServicePriceCreate,
    ServicePriceUpdate,
    ServiceStationFilter,
    ServiceStationReviewCreate,
    ServiceStationReviewUpdate,
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


# ==================== Service Station CRUD ====================

def create_service_station(
    db: Session,
    station_data: ServiceStationCreate,
    created_by_user_id: Optional[int] = None,
    created_by_admin_id: Optional[int] = None
) -> ServiceStation:
    """Создание СТО"""
    station_dict = station_data.model_dump(exclude={"service_prices"})
    station_dict["created_by_user_id"] = created_by_user_id
    station_dict["created_by_admin_id"] = created_by_admin_id
    
    # Если создает админ, сразу одобряем
    if created_by_admin_id:
        station_dict["status"] = ServiceStationStatus.APPROVED
    
    db_station = ServiceStation(**station_dict)
    db.add(db_station)
    db.flush()  # Получаем ID СТО
    
    # Добавляем цены на услуги
    if station_data.service_prices:
        for price_data in station_data.service_prices:
            service_price = ServicePrice(
                service_station_id=db_station.id,
                service_type=price_data.service_type.value,
                service_name=price_data.service_name,
                price=price_data.price,
                description=price_data.description,
                updated_by_admin_id=created_by_admin_id,
                updated_by_user_id=created_by_user_id
            )
            db.add(service_price)
    
    db.commit()
    db.refresh(db_station)
    return db_station


def get_service_station_by_id(db: Session, station_id: int) -> Optional[ServiceStation]:
    """Получение СТО по ID"""
    return db.query(ServiceStation).filter(ServiceStation.id == station_id).first()


def get_service_stations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[ServiceStationFilter] = None
) -> Tuple[List[ServiceStation], int]:
    """Получение списка СТО с фильтрацией"""
    query = db.query(ServiceStation)
    
    # Фильтр по статусу (по умолчанию только одобренные)
    if filters and filters.status:
        query = query.filter(ServiceStation.status == filters.status.value)
    else:
        query = query.filter(ServiceStation.status == ServiceStationStatus.APPROVED)
    
    # Фильтр по типу услуги (через цены)
    fuel_price_joined = False
    if filters and filters.service_type:
        try:
            service_type_enum = ServiceType(filters.service_type)
            query = query.join(ServicePrice).filter(
                ServicePrice.service_type == service_type_enum
            )
            fuel_price_joined = True
            if filters.max_price:
                query = query.filter(ServicePrice.price <= filters.max_price)
            if filters.min_price:
                query = query.filter(ServicePrice.price >= filters.min_price)
        except ValueError:
            pass
    elif filters and (filters.max_price or filters.min_price):
        query = query.join(ServicePrice)
        fuel_price_joined = True
        if filters.max_price:
            query = query.filter(ServicePrice.price <= filters.max_price)
        if filters.min_price:
            query = query.filter(ServicePrice.price >= filters.min_price)
    
    # Фильтр по минимальному рейтингу
    if filters and filters.min_rating is not None:
        query = query.filter(ServiceStation.rating >= filters.min_rating)
    
    # Фильтр по режиму работы
    if filters and filters.is_24_7 is not None:
        query = query.filter(ServiceStation.is_24_7 == filters.is_24_7)
    
    # Фильтр по наличию акций
    if filters and filters.has_promotions is not None:
        query = query.filter(ServiceStation.has_promotions == filters.has_promotions)
    
    # Фильтр по дополнительным услугам
    if filters and filters.has_parking is not None:
        query = query.filter(ServiceStation.has_parking == filters.has_parking)
    if filters and filters.has_waiting_room is not None:
        query = query.filter(ServiceStation.has_waiting_room == filters.has_waiting_room)
    if filters and filters.has_cafe is not None:
        query = query.filter(ServiceStation.has_cafe == filters.has_cafe)
    if filters and filters.accepts_cards is not None:
        query = query.filter(ServiceStation.accepts_cards == filters.accepts_cards)
    
    # Поиск по названию или адресу
    if filters and filters.search_query:
        search_term = f"%{filters.search_query}%"
        query = query.filter(
            or_(
                ServiceStation.name.ilike(search_term),
                ServiceStation.address.ilike(search_term),
                ServiceStation.description.ilike(search_term)
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
    stations = query.order_by(ServiceStation.rating.desc(), ServiceStation.reviews_count.desc()).offset(skip).limit(limit).all()
    
    return stations, total


def update_service_station(
    db: Session,
    station_id: int,
    station_update: ServiceStationUpdate
) -> Optional[ServiceStation]:
    """Обновление СТО"""
    station = get_service_station_by_id(db, station_id)
    if not station:
        return None
    
    update_data = station_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(station, field, value)
    
    db.commit()
    db.refresh(station)
    return station


def delete_service_station(db: Session, station_id: int) -> bool:
    """Удаление СТО"""
    station = get_service_station_by_id(db, station_id)
    if not station:
        return False
    
    db.delete(station)
    db.commit()
    return True


def approve_service_station(db: Session, station_id: int) -> Optional[ServiceStation]:
    """Одобрение СТО"""
    station = get_service_station_by_id(db, station_id)
    if not station:
        return None
    
    station.status = ServiceStationStatus.APPROVED
    station.approved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(station)
    return station


def reject_service_station(db: Session, station_id: int) -> Optional[ServiceStation]:
    """Отклонение СТО"""
    station = get_service_station_by_id(db, station_id)
    if not station:
        return None
    
    station.status = ServiceStationStatus.REJECTED
    
    db.commit()
    db.refresh(station)
    return station


# ==================== Service Price CRUD ====================

def create_or_update_service_price(
    db: Session,
    station_id: int,
    price_data: ServicePriceCreate,
    updated_by_user_id: Optional[int] = None,
    updated_by_admin_id: Optional[int] = None
) -> ServicePrice:
    """Создание или обновление цены на услугу"""
    service_price = ServicePrice(
        service_station_id=station_id,
        service_type=price_data.service_type.value,
        service_name=price_data.service_name,
        price=price_data.price,
        description=price_data.description,
        updated_by_user_id=updated_by_user_id,
        updated_by_admin_id=updated_by_admin_id
    )
    db.add(service_price)
    db.commit()
    db.refresh(service_price)
    return service_price


def update_service_price(
    db: Session,
    price_id: int,
    price_update: ServicePriceUpdate,
    updated_by_user_id: Optional[int] = None,
    updated_by_admin_id: Optional[int] = None
) -> Optional[ServicePrice]:
    """Обновление цены на услугу"""
    service_price = db.query(ServicePrice).filter(ServicePrice.id == price_id).first()
    if not service_price:
        return None
    
    update_data = price_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service_price, field, value)
    
    service_price.updated_by_user_id = updated_by_user_id
    service_price.updated_by_admin_id = updated_by_admin_id
    
    db.commit()
    db.refresh(service_price)
    return service_price


def bulk_update_service_prices(
    db: Session,
    station_id: int,
    prices: List[ServicePriceCreate],
    updated_by_user_id: Optional[int] = None,
    updated_by_admin_id: Optional[int] = None
) -> List[ServicePrice]:
    """Массовое обновление цен на услуги"""
    updated_prices = []
    for price_data in prices:
        price = create_or_update_service_price(
            db, station_id, price_data, updated_by_user_id, updated_by_admin_id
        )
        updated_prices.append(price)
    return updated_prices


def get_service_prices_by_station(db: Session, station_id: int) -> List[ServicePrice]:
    """Получение всех цен на услуги для СТО"""
    return db.query(ServicePrice).filter(
        ServicePrice.service_station_id == station_id
    ).order_by(ServicePrice.service_type, ServicePrice.created_at).all()


def delete_service_price(db: Session, price_id: int) -> bool:
    """Удаление цены на услугу"""
    service_price = db.query(ServicePrice).filter(ServicePrice.id == price_id).first()
    if not service_price:
        return False
    
    db.delete(service_price)
    db.commit()
    return True


# ==================== Photo CRUD ====================

def add_service_station_photo(
    db: Session,
    station_id: int,
    photo_url: str,
    is_main: bool = False,
    order: int = 0,
    uploaded_by_user_id: Optional[int] = None,
    uploaded_by_admin_id: Optional[int] = None
) -> ServiceStationPhoto:
    """Добавление фотографии к СТО"""
    # Если это главная фотография, снимаем флаг с других
    if is_main:
        db.query(ServiceStationPhoto).filter(
            ServiceStationPhoto.service_station_id == station_id,
            ServiceStationPhoto.is_main == True
        ).update({"is_main": False})
    
    photo = ServiceStationPhoto(
        service_station_id=station_id,
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


def get_service_station_photos(db: Session, station_id: int) -> List[ServiceStationPhoto]:
    """Получение всех фотографий СТО"""
    return db.query(ServiceStationPhoto).filter(
        ServiceStationPhoto.service_station_id == station_id
    ).order_by(ServiceStationPhoto.is_main.desc(), ServiceStationPhoto.order, ServiceStationPhoto.created_at).all()


def delete_service_station_photo(db: Session, photo_id: int) -> bool:
    """Удаление фотографии"""
    photo = db.query(ServiceStationPhoto).filter(ServiceStationPhoto.id == photo_id).first()
    if not photo:
        return False
    
    db.delete(photo)
    db.commit()
    return True


def set_main_photo(db: Session, station_id: int, photo_id: int) -> Optional[ServiceStationPhoto]:
    """Установка главной фотографии"""
    photo = db.query(ServiceStationPhoto).filter(
        and_(
            ServiceStationPhoto.id == photo_id,
            ServiceStationPhoto.service_station_id == station_id
        )
    ).first()
    if not photo:
        return None
    
    # Снимаем флаг с других фотографий
    db.query(ServiceStationPhoto).filter(
        and_(
            ServiceStationPhoto.service_station_id == station_id,
            ServiceStationPhoto.is_main == True
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
    review_data: ServiceStationReviewCreate
) -> ServiceStationReview:
    """Создание отзыва"""
    # Проверяем, есть ли уже отзыв от этого пользователя
    existing_review = db.query(ServiceStationReview).filter(
        and_(
            ServiceStationReview.service_station_id == station_id,
            ServiceStationReview.user_id == user_id
        )
    ).first()
    
    if existing_review:
        # Обновляем существующий отзыв
        existing_review.rating = review_data.rating
        existing_review.comment = review_data.comment
        db.commit()
        db.refresh(existing_review)
        review = existing_review
    else:
        # Создаем новый отзыв
        review = ServiceStationReview(
            service_station_id=station_id,
            user_id=user_id,
            rating=review_data.rating,
            comment=review_data.comment
        )
        db.add(review)
        db.commit()
        db.refresh(review)
    
    # Пересчитываем рейтинг СТО
    _recalculate_station_rating(db, station_id)
    
    return review


def get_reviews_by_station(
    db: Session,
    station_id: int,
    skip: int = 0,
    limit: int = 50
) -> Tuple[List[ServiceStationReview], int]:
    """Получение отзывов по СТО"""
    query = db.query(ServiceStationReview).filter(ServiceStationReview.service_station_id == station_id)
    total = query.count()
    reviews = query.order_by(ServiceStationReview.created_at.desc()).offset(skip).limit(limit).all()
    return reviews, total


def update_review(
    db: Session,
    review_id: int,
    user_id: int,
    review_update: ServiceStationReviewUpdate
) -> Optional[ServiceStationReview]:
    """Обновление отзыва"""
    review = db.query(ServiceStationReview).filter(
        and_(
            ServiceStationReview.id == review_id,
            ServiceStationReview.user_id == user_id
        )
    ).first()
    if not review:
        return None
    
    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)
    
    db.commit()
    db.refresh(review)
    
    # Пересчитываем рейтинг СТО
    _recalculate_station_rating(db, review.service_station_id)
    
    return review


def delete_review(db: Session, review_id: int, user_id: int) -> bool:
    """Удаление отзыва"""
    review = db.query(ServiceStationReview).filter(
        and_(
            ServiceStationReview.id == review_id,
            ServiceStationReview.user_id == user_id
        )
    ).first()
    if not review:
        return False
    
    station_id = review.service_station_id
    db.delete(review)
    db.commit()
    
    # Пересчитываем рейтинг СТО
    _recalculate_station_rating(db, station_id)
    
    return True


def _recalculate_station_rating(db: Session, station_id: int):
    """Пересчет рейтинга СТО на основе отзывов"""
    reviews = db.query(ServiceStationReview).filter(ServiceStationReview.service_station_id == station_id).all()
    
    if not reviews:
        rating = 0.0
        count = 0
    else:
        rating = sum(r.rating for r in reviews) / len(reviews)
        count = len(reviews)
    
    station = get_service_station_by_id(db, station_id)
    if station:
        station.rating = round(rating, 2)
        station.reviews_count = count
        db.commit()











