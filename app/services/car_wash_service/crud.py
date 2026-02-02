"""
CRUD операции для Car Wash Service
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from math import radians, cos, sin, asin, sqrt

from app.models.car_wash import (
    CarWash,
    CarWashService,
    CarWashPhoto,
    CarWashReview,
    WashServiceType,
    CarWashStatus,
)
from app.schemas.car_wash import (
    CarWashCreate,
    CarWashUpdate,
    CarWashServiceCreate,
    CarWashServiceUpdate,
    CarWashFilter,
    CarWashReviewCreate,
    CarWashReviewUpdate,
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


# ==================== Car Wash CRUD ====================

def create_car_wash(
    db: Session,
    car_wash_data: CarWashCreate,
    created_by_user_id: Optional[int] = None,
    created_by_admin_id: Optional[int] = None
) -> CarWash:
    """Создание автомойки"""
    car_wash_dict = car_wash_data.model_dump(exclude={"services"})
    car_wash_dict["created_by_user_id"] = created_by_user_id
    car_wash_dict["created_by_admin_id"] = created_by_admin_id
    
    # Если создает админ, сразу одобряем
    if created_by_admin_id:
        car_wash_dict["status"] = CarWashStatus.APPROVED
    
    db_car_wash = CarWash(**car_wash_dict)
    db.add(db_car_wash)
    db.flush()  # Получаем ID автомойки
    
    # Добавляем услуги
    if car_wash_data.services:
        for service_data in car_wash_data.services:
            car_wash_service = CarWashService(
                car_wash_id=db_car_wash.id,
                service_type=service_data.service_type.value,
                service_name=service_data.service_name,
                price=service_data.price,
                description=service_data.description,
                duration_minutes=service_data.duration_minutes,
                updated_by_admin_id=created_by_admin_id,
                updated_by_user_id=created_by_user_id
            )
            db.add(car_wash_service)
    
    db.commit()
    db.refresh(db_car_wash)
    return db_car_wash


def get_car_wash_by_id(db: Session, car_wash_id: int) -> Optional[CarWash]:
    """Получение автомойки по ID"""
    return db.query(CarWash).filter(CarWash.id == car_wash_id).first()


def get_car_washes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[CarWashFilter] = None
) -> Tuple[List[CarWash], int]:
    """Получение списка автомоек с фильтрацией"""
    query = db.query(CarWash)
    
    # Фильтр по статусу (по умолчанию только одобренные)
    if filters and filters.status:
        query = query.filter(CarWash.status == filters.status.value)
    else:
        query = query.filter(CarWash.status == CarWashStatus.APPROVED)
    
    # Фильтр по типу услуги (через услуги)
    service_joined = False
    if filters and filters.service_type:
        try:
            service_type_enum = WashServiceType(filters.service_type)
            query = query.join(CarWashService).filter(
                CarWashService.service_type == service_type_enum
            )
            service_joined = True
            if filters.max_price:
                query = query.filter(CarWashService.price <= filters.max_price)
            if filters.min_price:
                query = query.filter(CarWashService.price >= filters.min_price)
        except ValueError:
            pass
    elif filters and (filters.max_price or filters.min_price):
        query = query.join(CarWashService)
        service_joined = True
        if filters.max_price:
            query = query.filter(CarWashService.price <= filters.max_price)
        if filters.min_price:
            query = query.filter(CarWashService.price >= filters.min_price)
    
    # Фильтр по минимальному рейтингу
    if filters and filters.min_rating is not None:
        query = query.filter(CarWash.rating >= filters.min_rating)
    
    # Фильтр по режиму работы
    if filters and filters.is_24_7 is not None:
        query = query.filter(CarWash.is_24_7 == filters.is_24_7)
    
    # Фильтр по наличию акций
    if filters and filters.has_promotions is not None:
        query = query.filter(CarWash.has_promotions == filters.has_promotions)
    
    # Фильтр по дополнительным услугам
    if filters and filters.has_parking is not None:
        query = query.filter(CarWash.has_parking == filters.has_parking)
    if filters and filters.has_waiting_room is not None:
        query = query.filter(CarWash.has_waiting_room == filters.has_waiting_room)
    if filters and filters.has_cafe is not None:
        query = query.filter(CarWash.has_cafe == filters.has_cafe)
    if filters and filters.accepts_cards is not None:
        query = query.filter(CarWash.accepts_cards == filters.accepts_cards)
    if filters and filters.has_vacuum is not None:
        query = query.filter(CarWash.has_vacuum == filters.has_vacuum)
    if filters and filters.has_drying is not None:
        query = query.filter(CarWash.has_drying == filters.has_drying)
    if filters and filters.has_self_service is not None:
        query = query.filter(CarWash.has_self_service == filters.has_self_service)
    
    # Поиск по названию или адресу
    if filters and filters.search_query:
        search_term = f"%{filters.search_query}%"
        query = query.filter(
            or_(
                CarWash.name.ilike(search_term),
                CarWash.address.ilike(search_term),
                CarWash.description.ilike(search_term)
            )
        )
    
    # Поиск по близости
    if filters and filters.latitude and filters.longitude and filters.radius_km:
        all_car_washes = query.all()
        filtered_car_washes = []
        for car_wash in all_car_washes:
            distance = haversine_distance(
                filters.latitude,
                filters.longitude,
                car_wash.latitude,
                car_wash.longitude
            )
            if distance <= filters.radius_km:
                filtered_car_washes.append(car_wash)
        
        total = len(filtered_car_washes)
        car_washes = filtered_car_washes[skip:skip + limit]
        return car_washes, total
    
    # Подсчет общего количества
    total = query.count()
    
    # Применяем пагинацию
    car_washes = query.order_by(CarWash.rating.desc(), CarWash.reviews_count.desc()).offset(skip).limit(limit).all()
    
    return car_washes, total


def update_car_wash(
    db: Session,
    car_wash_id: int,
    car_wash_update: CarWashUpdate
) -> Optional[CarWash]:
    """Обновление автомойки"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        return None
    
    update_data = car_wash_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(car_wash, field, value)
    
    db.commit()
    db.refresh(car_wash)
    return car_wash


def delete_car_wash(db: Session, car_wash_id: int) -> bool:
    """Удаление автомойки"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        return False
    
    db.delete(car_wash)
    db.commit()
    return True


def approve_car_wash(db: Session, car_wash_id: int) -> Optional[CarWash]:
    """Одобрение автомойки"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        return None
    
    car_wash.status = CarWashStatus.APPROVED
    car_wash.approved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(car_wash)
    return car_wash


def reject_car_wash(db: Session, car_wash_id: int) -> Optional[CarWash]:
    """Отклонение автомойки"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        return None
    
    car_wash.status = CarWashStatus.REJECTED
    
    db.commit()
    db.refresh(car_wash)
    return car_wash


# ==================== Car Wash Service CRUD ====================

def create_or_update_car_wash_service(
    db: Session,
    car_wash_id: int,
    service_data: CarWashServiceCreate,
    updated_by_user_id: Optional[int] = None,
    updated_by_admin_id: Optional[int] = None
) -> CarWashService:
    """Создание или обновление услуги автомойки"""
    car_wash_service = CarWashService(
        car_wash_id=car_wash_id,
        service_type=service_data.service_type.value,
        service_name=service_data.service_name,
        price=service_data.price,
        description=service_data.description,
        duration_minutes=service_data.duration_minutes,
        updated_by_user_id=updated_by_user_id,
        updated_by_admin_id=updated_by_admin_id
    )
    db.add(car_wash_service)
    db.commit()
    db.refresh(car_wash_service)
    return car_wash_service


def update_car_wash_service(
    db: Session,
    service_id: int,
    service_update: CarWashServiceUpdate,
    updated_by_user_id: Optional[int] = None,
    updated_by_admin_id: Optional[int] = None
) -> Optional[CarWashService]:
    """Обновление услуги автомойки"""
    car_wash_service = db.query(CarWashService).filter(CarWashService.id == service_id).first()
    if not car_wash_service:
        return None
    
    update_data = service_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(car_wash_service, field, value)
    
    car_wash_service.updated_by_user_id = updated_by_user_id
    car_wash_service.updated_by_admin_id = updated_by_admin_id
    
    db.commit()
    db.refresh(car_wash_service)
    return car_wash_service


def bulk_update_car_wash_services(
    db: Session,
    car_wash_id: int,
    services: List[CarWashServiceCreate],
    updated_by_user_id: Optional[int] = None,
    updated_by_admin_id: Optional[int] = None
) -> List[CarWashService]:
    """Массовое обновление услуг автомойки"""
    updated_services = []
    for service_data in services:
        service = create_or_update_car_wash_service(
            db, car_wash_id, service_data, updated_by_user_id, updated_by_admin_id
        )
        updated_services.append(service)
    return updated_services


def get_car_wash_services_by_car_wash(db: Session, car_wash_id: int) -> List[CarWashService]:
    """Получение всех услуг автомойки"""
    return db.query(CarWashService).filter(
        CarWashService.car_wash_id == car_wash_id
    ).order_by(CarWashService.service_type, CarWashService.created_at).all()


def delete_car_wash_service(db: Session, service_id: int) -> bool:
    """Удаление услуги автомойки"""
    car_wash_service = db.query(CarWashService).filter(CarWashService.id == service_id).first()
    if not car_wash_service:
        return False
    
    db.delete(car_wash_service)
    db.commit()
    return True


# ==================== Photo CRUD ====================

def add_car_wash_photo(
    db: Session,
    car_wash_id: int,
    photo_url: str,
    is_main: bool = False,
    order: int = 0,
    uploaded_by_user_id: Optional[int] = None,
    uploaded_by_admin_id: Optional[int] = None
) -> CarWashPhoto:
    """Добавление фотографии к автомойке"""
    # Если это главная фотография, снимаем флаг с других
    if is_main:
        db.query(CarWashPhoto).filter(
            CarWashPhoto.car_wash_id == car_wash_id,
            CarWashPhoto.is_main == True
        ).update({"is_main": False})
    
    photo = CarWashPhoto(
        car_wash_id=car_wash_id,
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


def get_car_wash_photos(db: Session, car_wash_id: int) -> List[CarWashPhoto]:
    """Получение всех фотографий автомойки"""
    return db.query(CarWashPhoto).filter(
        CarWashPhoto.car_wash_id == car_wash_id
    ).order_by(CarWashPhoto.is_main.desc(), CarWashPhoto.order, CarWashPhoto.created_at).all()


def delete_car_wash_photo(db: Session, photo_id: int) -> bool:
    """Удаление фотографии"""
    photo = db.query(CarWashPhoto).filter(CarWashPhoto.id == photo_id).first()
    if not photo:
        return False
    
    db.delete(photo)
    db.commit()
    return True


def set_main_photo(db: Session, car_wash_id: int, photo_id: int) -> Optional[CarWashPhoto]:
    """Установка главной фотографии"""
    photo = db.query(CarWashPhoto).filter(
        and_(
            CarWashPhoto.id == photo_id,
            CarWashPhoto.car_wash_id == car_wash_id
        )
    ).first()
    if not photo:
        return None
    
    # Снимаем флаг с других фотографий
    db.query(CarWashPhoto).filter(
        and_(
            CarWashPhoto.car_wash_id == car_wash_id,
            CarWashPhoto.is_main == True
        )
    ).update({"is_main": False})
    
    photo.is_main = True
    db.commit()
    db.refresh(photo)
    return photo


# ==================== Review CRUD ====================

def create_review(
    db: Session,
    car_wash_id: int,
    user_id: int,
    review_data: CarWashReviewCreate
) -> CarWashReview:
    """Создание отзыва"""
    # Проверяем, есть ли уже отзыв от этого пользователя
    existing_review = db.query(CarWashReview).filter(
        and_(
            CarWashReview.car_wash_id == car_wash_id,
            CarWashReview.user_id == user_id
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
        review = CarWashReview(
            car_wash_id=car_wash_id,
            user_id=user_id,
            rating=review_data.rating,
            comment=review_data.comment
        )
        db.add(review)
        db.commit()
        db.refresh(review)
    
    # Пересчитываем рейтинг автомойки
    _recalculate_car_wash_rating(db, car_wash_id)
    
    return review


def get_reviews_by_car_wash(
    db: Session,
    car_wash_id: int,
    skip: int = 0,
    limit: int = 50
) -> Tuple[List[CarWashReview], int]:
    """Получение отзывов по автомойке"""
    query = db.query(CarWashReview).filter(CarWashReview.car_wash_id == car_wash_id)
    total = query.count()
    reviews = query.order_by(CarWashReview.created_at.desc()).offset(skip).limit(limit).all()
    return reviews, total


def update_review(
    db: Session,
    review_id: int,
    user_id: int,
    review_update: CarWashReviewUpdate
) -> Optional[CarWashReview]:
    """Обновление отзыва"""
    review = db.query(CarWashReview).filter(
        and_(
            CarWashReview.id == review_id,
            CarWashReview.user_id == user_id
        )
    ).first()
    if not review:
        return None
    
    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)
    
    db.commit()
    db.refresh(review)
    
    # Пересчитываем рейтинг автомойки
    _recalculate_car_wash_rating(db, review.car_wash_id)
    
    return review


def delete_review(db: Session, review_id: int, user_id: int) -> bool:
    """Удаление отзыва"""
    review = db.query(CarWashReview).filter(
        and_(
            CarWashReview.id == review_id,
            CarWashReview.user_id == user_id
        )
    ).first()
    if not review:
        return False
    
    car_wash_id = review.car_wash_id
    db.delete(review)
    db.commit()
    
    # Пересчитываем рейтинг автомойки
    _recalculate_car_wash_rating(db, car_wash_id)
    
    return True


def _recalculate_car_wash_rating(db: Session, car_wash_id: int):
    """Пересчет рейтинга автомойки на основе отзывов"""
    reviews = db.query(CarWashReview).filter(CarWashReview.car_wash_id == car_wash_id).all()
    
    if not reviews:
        rating = 0.0
        count = 0
    else:
        rating = sum(r.rating for r in reviews) / len(reviews)
        count = len(reviews)
    
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if car_wash:
        car_wash.rating = round(rating, 2)
        car_wash.reviews_count = count
        db.commit()











