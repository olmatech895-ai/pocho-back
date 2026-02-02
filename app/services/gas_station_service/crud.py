"""
CRUD операции для Gas Station Service
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func as sql_func
from math import radians, cos, sin, asin, sqrt

from app.models.gas_station import (
    GasStation,
    FuelPrice,
    GasStationPhoto,
    Review,
    FuelType,
    StationStatus,
)
from app.schemas.gas_station import (
    GasStationCreate,
    GasStationUpdate,
    FuelPriceCreate,
    FuelPriceUpdate,
    GasStationFilter,
    ReviewCreate,
    ReviewUpdate,
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


# ==================== Gas Station CRUD ====================

def create_gas_station(
    db: Session,
    station_data: GasStationCreate,
    created_by_user_id: Optional[int] = None,
    created_by_admin_id: Optional[int] = None
) -> GasStation:
    """Создание заправочной станции"""
    station_dict = station_data.model_dump(exclude={"fuel_prices"})
    station_dict["created_by_user_id"] = created_by_user_id
    station_dict["created_by_admin_id"] = created_by_admin_id
    
    # Если создает админ, сразу одобряем
    if created_by_admin_id:
        station_dict["status"] = StationStatus.APPROVED
    
    db_station = GasStation(**station_dict)
    db.add(db_station)
    db.flush()  # Получаем ID станции
    
    # Добавляем цены на топливо
    if station_data.fuel_prices:
        for price_data in station_data.fuel_prices:
            fuel_price = FuelPrice(
                gas_station_id=db_station.id,
                fuel_type=price_data.fuel_type.value,
                price=price_data.price,
                updated_by_admin_id=created_by_admin_id,
                updated_by_user_id=created_by_user_id
            )
            db.add(fuel_price)
    
    db.commit()
    db.refresh(db_station)
    return db_station


def get_gas_station_by_id(db: Session, station_id: int) -> Optional[GasStation]:
    """Получение заправочной станции по ID"""
    return db.query(GasStation).filter(GasStation.id == station_id).first()


def get_gas_stations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[GasStationFilter] = None
) -> Tuple[List[GasStation], int]:
    """Получение списка заправочных станций с фильтрацией"""
    query = db.query(GasStation)
    
    # Фильтр по статусу (по умолчанию только одобренные)
    if filters and filters.status:
        query = query.filter(GasStation.status == filters.status.value)
    else:
        query = query.filter(GasStation.status == StationStatus.APPROVED)
    
    # Фильтр по типу топлива и максимальной цене (через цены)
    fuel_price_joined = False
    if filters and filters.fuel_type:
        # Конвертируем строку в enum, если нужно
        try:
            fuel_type_enum = FuelType(filters.fuel_type)
            query = query.join(FuelPrice).filter(
                FuelPrice.fuel_type == fuel_type_enum
            )
            fuel_price_joined = True
            if filters.max_price:
                query = query.filter(FuelPrice.price <= filters.max_price)
        except ValueError:
            # Если тип топлива неверный, просто игнорируем фильтр
            pass
    elif filters and filters.max_price:
        # Если только фильтр по цене без типа топлива
        query = query.join(FuelPrice).filter(FuelPrice.price <= filters.max_price)
        fuel_price_joined = True
    
    # Фильтр по минимальному рейтингу
    if filters and filters.min_rating is not None:
        query = query.filter(GasStation.rating >= filters.min_rating)
    
    # Фильтр по режиму работы
    if filters and filters.is_24_7 is not None:
        query = query.filter(GasStation.is_24_7 == filters.is_24_7)
    
    # Фильтр по наличию акций
    if filters and filters.has_promotions is not None:
        query = query.filter(GasStation.has_promotions == filters.has_promotions)
    
    # Поиск по названию или адресу
    if filters and filters.search_query:
        search_term = f"%{filters.search_query}%"
        query = query.filter(
            or_(
                GasStation.name.ilike(search_term),
                GasStation.address.ilike(search_term)
            )
        )
    
    # Поиск по близости
    if filters and filters.latitude and filters.longitude and filters.radius_km:
        # Получаем все станции и фильтруем по расстоянию
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
    stations = query.order_by(GasStation.rating.desc(), GasStation.reviews_count.desc()).offset(skip).limit(limit).all()
    
    return stations, total


def update_gas_station(
    db: Session,
    station_id: int,
    station_update: GasStationUpdate
) -> Optional[GasStation]:
    """Обновление заправочной станции"""
    station = get_gas_station_by_id(db, station_id)
    if not station:
        return None
    
    update_data = station_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(station, field, value)
    
    db.commit()
    db.refresh(station)
    return station


def delete_gas_station(db: Session, station_id: int) -> bool:
    """Удаление заправочной станции"""
    station = get_gas_station_by_id(db, station_id)
    if not station:
        return False
    
    db.delete(station)
    db.commit()
    return True


def approve_gas_station(db: Session, station_id: int) -> Optional[GasStation]:
    """Одобрение заправочной станции"""
    station = get_gas_station_by_id(db, station_id)
    if not station:
        return None
    
    station.status = StationStatus.APPROVED
    station.approved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(station)
    return station


def reject_gas_station(db: Session, station_id: int) -> Optional[GasStation]:
    """Отклонение заправочной станции"""
    station = get_gas_station_by_id(db, station_id)
    if not station:
        return None
    
    station.status = StationStatus.REJECTED
    
    db.commit()
    db.refresh(station)
    return station


# ==================== Fuel Price CRUD ====================

def create_or_update_fuel_price(
    db: Session,
    station_id: int,
    price_data: FuelPriceCreate,
    updated_by_user_id: Optional[int] = None,
    updated_by_admin_id: Optional[int] = None
) -> FuelPrice:
    """Создание или обновление цены на топливо"""
    existing_price = db.query(FuelPrice).filter(
        and_(
            FuelPrice.gas_station_id == station_id,
            FuelPrice.fuel_type == price_data.fuel_type.value
        )
    ).first()
    
    if existing_price:
        existing_price.price = price_data.price
        existing_price.updated_by_user_id = updated_by_user_id
        existing_price.updated_by_admin_id = updated_by_admin_id
        db.commit()
        db.refresh(existing_price)
        return existing_price
    else:
        fuel_price = FuelPrice(
            gas_station_id=station_id,
            fuel_type=price_data.fuel_type.value,
            price=price_data.price,
            updated_by_user_id=updated_by_user_id,
            updated_by_admin_id=updated_by_admin_id
        )
        db.add(fuel_price)
        db.commit()
        db.refresh(fuel_price)
        return fuel_price


def update_fuel_price(
    db: Session,
    price_id: int,
    price_update: FuelPriceUpdate,
    updated_by_user_id: Optional[int] = None,
    updated_by_admin_id: Optional[int] = None
) -> Optional[FuelPrice]:
    """Обновление цены на топливо"""
    fuel_price = db.query(FuelPrice).filter(FuelPrice.id == price_id).first()
    if not fuel_price:
        return None
    
    fuel_price.price = price_update.price
    fuel_price.updated_by_user_id = updated_by_user_id
    fuel_price.updated_by_admin_id = updated_by_admin_id
    
    db.commit()
    db.refresh(fuel_price)
    return fuel_price


def bulk_update_fuel_prices(
    db: Session,
    station_id: int,
    prices: List[FuelPriceCreate],
    updated_by_user_id: Optional[int] = None,
    updated_by_admin_id: Optional[int] = None
) -> List[FuelPrice]:
    """Массовое обновление цен на топливо"""
    updated_prices = []
    for price_data in prices:
        price = create_or_update_fuel_price(
            db, station_id, price_data, updated_by_user_id, updated_by_admin_id
        )
        updated_prices.append(price)
    return updated_prices


def get_fuel_prices_by_station(db: Session, station_id: int) -> List[FuelPrice]:
    """Получение всех цен на топливо для станции"""
    return db.query(FuelPrice).filter(
        FuelPrice.gas_station_id == station_id
    ).order_by(FuelPrice.fuel_type).all()


# ==================== Photo CRUD ====================

def add_gas_station_photo(
    db: Session,
    station_id: int,
    photo_url: str,
    is_main: bool = False,
    order: int = 0,
    uploaded_by_user_id: Optional[int] = None,
    uploaded_by_admin_id: Optional[int] = None
) -> GasStationPhoto:
    """Добавление фотографии к заправочной станции"""
    # Если это главная фотография, снимаем флаг с других
    if is_main:
        db.query(GasStationPhoto).filter(
            GasStationPhoto.gas_station_id == station_id,
            GasStationPhoto.is_main == True
        ).update({"is_main": False})
    
    photo = GasStationPhoto(
        gas_station_id=station_id,
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


def get_gas_station_photos(db: Session, station_id: int) -> List[GasStationPhoto]:
    """Получение всех фотографий станции"""
    return db.query(GasStationPhoto).filter(
        GasStationPhoto.gas_station_id == station_id
    ).order_by(GasStationPhoto.is_main.desc(), GasStationPhoto.order, GasStationPhoto.created_at).all()


def delete_gas_station_photo(db: Session, photo_id: int) -> bool:
    """Удаление фотографии"""
    photo = db.query(GasStationPhoto).filter(GasStationPhoto.id == photo_id).first()
    if not photo:
        return False
    
    db.delete(photo)
    db.commit()
    return True


def set_main_photo(db: Session, station_id: int, photo_id: int) -> Optional[GasStationPhoto]:
    """Установка главной фотографии"""
    photo = db.query(GasStationPhoto).filter(
        and_(
            GasStationPhoto.id == photo_id,
            GasStationPhoto.gas_station_id == station_id
        )
    ).first()
    if not photo:
        return None
    
    # Снимаем флаг с других фотографий
    db.query(GasStationPhoto).filter(
        and_(
            GasStationPhoto.gas_station_id == station_id,
            GasStationPhoto.is_main == True
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
    review_data: ReviewCreate
) -> Review:
    """Создание отзыва"""
    # Проверяем, есть ли уже отзыв от этого пользователя
    existing_review = db.query(Review).filter(
        and_(
            Review.gas_station_id == station_id,
            Review.user_id == user_id
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
        review = Review(
            gas_station_id=station_id,
            user_id=user_id,
            rating=review_data.rating,
            comment=review_data.comment
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
) -> Tuple[List[Review], int]:
    """Получение отзывов по станции"""
    query = db.query(Review).filter(Review.gas_station_id == station_id)
    total = query.count()
    reviews = query.order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    return reviews, total


def update_review(
    db: Session,
    review_id: int,
    user_id: int,
    review_update: ReviewUpdate
) -> Optional[Review]:
    """Обновление отзыва"""
    review = db.query(Review).filter(
        and_(
            Review.id == review_id,
            Review.user_id == user_id
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
    _recalculate_station_rating(db, review.gas_station_id)
    
    return review


def delete_review(db: Session, review_id: int, user_id: int) -> bool:
    """Удаление отзыва"""
    review = db.query(Review).filter(
        and_(
            Review.id == review_id,
            Review.user_id == user_id
        )
    ).first()
    if not review:
        return False
    
    station_id = review.gas_station_id
    db.delete(review)
    db.commit()
    
    # Пересчитываем рейтинг станции
    _recalculate_station_rating(db, station_id)
    
    return True


def _recalculate_station_rating(db: Session, station_id: int):
    """Пересчет рейтинга станции на основе отзывов"""
    reviews = db.query(Review).filter(Review.gas_station_id == station_id).all()
    
    if not reviews:
        rating = 0.0
        count = 0
    else:
        rating = sum(r.rating for r in reviews) / len(reviews)
        count = len(reviews)
    
    station = get_gas_station_by_id(db, station_id)
    if station:
        station.rating = round(rating, 2)
        station.reviews_count = count
        db.commit()

