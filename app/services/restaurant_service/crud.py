"""
CRUD операции для Restaurant Service
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from math import radians, cos, sin, asin, sqrt

from app.models.restaurant import (
    Restaurant,
    MenuCategory,
    MenuItem,
    RestaurantPhoto,
    RestaurantReview,
    CuisineType,
    RestaurantStatus,
)
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantUpdate,
    MenuCategoryCreate,
    MenuCategoryUpdate,
    MenuItemCreate,
    MenuItemUpdate,
    RestaurantFilter,
    RestaurantReviewCreate,
    RestaurantReviewUpdate,
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


# ==================== Restaurant CRUD ====================

def create_restaurant(
    db: Session,
    restaurant_data: RestaurantCreate,
    created_by_user_id: Optional[int] = None,
    created_by_admin_id: Optional[int] = None
) -> Restaurant:
    """Создание ресторана"""
    restaurant_dict = restaurant_data.model_dump(exclude={"menu_categories"})
    restaurant_dict["created_by_user_id"] = created_by_user_id
    restaurant_dict["created_by_admin_id"] = created_by_admin_id
    restaurant_dict["cuisine_type"] = restaurant_data.cuisine_type.value
    
    # Если создает админ, сразу одобряем
    if created_by_admin_id:
        restaurant_dict["status"] = RestaurantStatus.APPROVED
    
    db_restaurant = Restaurant(**restaurant_dict)
    db.add(db_restaurant)
    db.flush()  # Получаем ID ресторана
    
    # Добавляем категории меню и блюда
    if restaurant_data.menu_categories:
        for category_data in restaurant_data.menu_categories:
            category_dict = category_data.model_dump(exclude={"items"})
            menu_category = MenuCategory(
                restaurant_id=db_restaurant.id,
                **category_dict
            )
            db.add(menu_category)
            db.flush()
            
            # Добавляем блюда в категорию
            if category_data.items:
                for item_data in category_data.items:
                    menu_item = MenuItem(
                        category_id=menu_category.id,
                        restaurant_id=db_restaurant.id,
                        **item_data.model_dump()
                    )
                    db.add(menu_item)
    
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant


def get_restaurant_by_id(db: Session, restaurant_id: int) -> Optional[Restaurant]:
    """Получение ресторана по ID"""
    return db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()


def get_restaurants(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[RestaurantFilter] = None
) -> Tuple[List[Restaurant], int]:
    """Получение списка ресторанов с фильтрацией"""
    query = db.query(Restaurant)
    
    # Фильтр по статусу (по умолчанию только одобренные)
    if filters and filters.status:
        query = query.filter(Restaurant.status == filters.status.value)
    else:
        query = query.filter(Restaurant.status == RestaurantStatus.APPROVED)
    
    # Фильтр по типу кухни
    if filters and filters.cuisine_type:
        try:
            cuisine_type_enum = CuisineType(filters.cuisine_type)
            query = query.filter(Restaurant.cuisine_type == cuisine_type_enum)
        except ValueError:
            pass
    
    # Фильтр по среднему чеку
    if filters and filters.min_average_check is not None:
        query = query.filter(Restaurant.average_check >= filters.min_average_check)
    if filters and filters.max_average_check is not None:
        query = query.filter(Restaurant.average_check <= filters.max_average_check)
    
    # Фильтр по минимальному рейтингу
    if filters and filters.min_rating is not None:
        query = query.filter(Restaurant.rating >= filters.min_rating)
    
    # Фильтр по режиму работы
    if filters and filters.is_24_7 is not None:
        query = query.filter(Restaurant.is_24_7 == filters.is_24_7)
    
    # Фильтр по наличию акций
    if filters and filters.has_promotions is not None:
        query = query.filter(Restaurant.has_promotions == filters.has_promotions)
    
    # Фильтр по дополнительным услугам
    if filters and filters.has_booking is not None:
        query = query.filter(Restaurant.has_booking == filters.has_booking)
    if filters and filters.has_delivery is not None:
        query = query.filter(Restaurant.has_delivery == filters.has_delivery)
    if filters and filters.has_parking is not None:
        query = query.filter(Restaurant.has_parking == filters.has_parking)
    if filters and filters.has_wifi is not None:
        query = query.filter(Restaurant.has_wifi == filters.has_wifi)
    
    # Поиск по названию или адресу
    if filters and filters.search_query:
        search_term = f"%{filters.search_query}%"
        query = query.filter(
            or_(
                Restaurant.name.ilike(search_term),
                Restaurant.address.ilike(search_term),
                Restaurant.description.ilike(search_term)
            )
        )
    
    # Поиск по близости
    if filters and filters.latitude and filters.longitude and filters.radius_km:
        all_restaurants = query.all()
        filtered_restaurants = []
        for restaurant in all_restaurants:
            distance = haversine_distance(
                filters.latitude,
                filters.longitude,
                restaurant.latitude,
                restaurant.longitude
            )
            if distance <= filters.radius_km:
                filtered_restaurants.append(restaurant)
        
        total = len(filtered_restaurants)
        restaurants = filtered_restaurants[skip:skip + limit]
        return restaurants, total
    
    # Подсчет общего количества
    total = query.count()
    
    # Применяем пагинацию
    restaurants = query.order_by(Restaurant.rating.desc(), Restaurant.reviews_count.desc()).offset(skip).limit(limit).all()
    
    return restaurants, total


def update_restaurant(
    db: Session,
    restaurant_id: int,
    restaurant_update: RestaurantUpdate
) -> Optional[Restaurant]:
    """Обновление ресторана"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        return None
    
    update_data = restaurant_update.model_dump(exclude_unset=True)
    # Обрабатываем cuisine_type отдельно
    if "cuisine_type" in update_data and update_data["cuisine_type"]:
        update_data["cuisine_type"] = update_data["cuisine_type"].value
    
    for field, value in update_data.items():
        setattr(restaurant, field, value)
    
    db.commit()
    db.refresh(restaurant)
    return restaurant


def delete_restaurant(db: Session, restaurant_id: int) -> bool:
    """Удаление ресторана"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        return False
    
    db.delete(restaurant)
    db.commit()
    return True


def approve_restaurant(db: Session, restaurant_id: int) -> Optional[Restaurant]:
    """Одобрение ресторана"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        return None
    
    restaurant.status = RestaurantStatus.APPROVED
    restaurant.approved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(restaurant)
    return restaurant


def reject_restaurant(db: Session, restaurant_id: int) -> Optional[Restaurant]:
    """Отклонение ресторана"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        return None
    
    restaurant.status = RestaurantStatus.REJECTED
    
    db.commit()
    db.refresh(restaurant)
    return restaurant


# ==================== Menu Category CRUD ====================

def create_menu_category(
    db: Session,
    restaurant_id: int,
    category_data: MenuCategoryCreate
) -> MenuCategory:
    """Создание категории меню"""
    category_dict = category_data.model_dump(exclude={"items"})
    menu_category = MenuCategory(
        restaurant_id=restaurant_id,
        **category_dict
    )
    db.add(menu_category)
    db.flush()
    
    # Добавляем блюда в категорию
    if category_data.items:
        for item_data in category_data.items:
            menu_item = MenuItem(
                category_id=menu_category.id,
                restaurant_id=restaurant_id,
                **item_data.model_dump()
            )
            db.add(menu_item)
    
    db.commit()
    db.refresh(menu_category)
    return menu_category


def get_menu_categories_by_restaurant(db: Session, restaurant_id: int) -> List[MenuCategory]:
    """Получение всех категорий меню ресторана"""
    return db.query(MenuCategory).filter(
        MenuCategory.restaurant_id == restaurant_id
    ).order_by(MenuCategory.order, MenuCategory.created_at).all()


def update_menu_category(
    db: Session,
    category_id: int,
    category_update: MenuCategoryUpdate
) -> Optional[MenuCategory]:
    """Обновление категории меню"""
    category = db.query(MenuCategory).filter(MenuCategory.id == category_id).first()
    if not category:
        return None
    
    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    return category


def delete_menu_category(db: Session, category_id: int) -> bool:
    """Удаление категории меню"""
    category = db.query(MenuCategory).filter(MenuCategory.id == category_id).first()
    if not category:
        return False
    
    db.delete(category)
    db.commit()
    return True


# ==================== Menu Item CRUD ====================

def create_menu_item(
    db: Session,
    category_id: int,
    restaurant_id: int,
    item_data: MenuItemCreate
) -> MenuItem:
    """Создание блюда в меню"""
    menu_item = MenuItem(
        category_id=category_id,
        restaurant_id=restaurant_id,
        **item_data.model_dump()
    )
    db.add(menu_item)
    db.commit()
    db.refresh(menu_item)
    return menu_item


def get_menu_items_by_category(db: Session, category_id: int) -> List[MenuItem]:
    """Получение всех блюд категории"""
    return db.query(MenuItem).filter(
        MenuItem.category_id == category_id
    ).order_by(MenuItem.order, MenuItem.created_at).all()


def get_menu_items_by_restaurant(db: Session, restaurant_id: int) -> List[MenuItem]:
    """Получение всех блюд ресторана"""
    return db.query(MenuItem).filter(
        MenuItem.restaurant_id == restaurant_id
    ).order_by(MenuItem.order, MenuItem.created_at).all()


def update_menu_item(
    db: Session,
    item_id: int,
    item_update: MenuItemUpdate
) -> Optional[MenuItem]:
    """Обновление блюда"""
    menu_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not menu_item:
        return None
    
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(menu_item, field, value)
    
    db.commit()
    db.refresh(menu_item)
    return menu_item


def delete_menu_item(db: Session, item_id: int) -> bool:
    """Удаление блюда"""
    menu_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not menu_item:
        return False
    
    db.delete(menu_item)
    db.commit()
    return True


# ==================== Photo CRUD ====================

def add_restaurant_photo(
    db: Session,
    restaurant_id: int,
    photo_url: str,
    is_main: bool = False,
    order: int = 0,
    uploaded_by_user_id: Optional[int] = None,
    uploaded_by_admin_id: Optional[int] = None
) -> RestaurantPhoto:
    """Добавление фотографии к ресторану"""
    # Если это главная фотография, снимаем флаг с других
    if is_main:
        db.query(RestaurantPhoto).filter(
            RestaurantPhoto.restaurant_id == restaurant_id,
            RestaurantPhoto.is_main == True
        ).update({"is_main": False})
    
    photo = RestaurantPhoto(
        restaurant_id=restaurant_id,
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


def get_restaurant_photos(db: Session, restaurant_id: int) -> List[RestaurantPhoto]:
    """Получение всех фотографий ресторана"""
    return db.query(RestaurantPhoto).filter(
        RestaurantPhoto.restaurant_id == restaurant_id
    ).order_by(RestaurantPhoto.is_main.desc(), RestaurantPhoto.order, RestaurantPhoto.created_at).all()


def delete_restaurant_photo(db: Session, photo_id: int) -> bool:
    """Удаление фотографии"""
    photo = db.query(RestaurantPhoto).filter(RestaurantPhoto.id == photo_id).first()
    if not photo:
        return False
    
    db.delete(photo)
    db.commit()
    return True


def set_main_photo(db: Session, restaurant_id: int, photo_id: int) -> Optional[RestaurantPhoto]:
    """Установка главной фотографии"""
    photo = db.query(RestaurantPhoto).filter(
        and_(
            RestaurantPhoto.id == photo_id,
            RestaurantPhoto.restaurant_id == restaurant_id
        )
    ).first()
    if not photo:
        return None
    
    # Снимаем флаг с других фотографий
    db.query(RestaurantPhoto).filter(
        and_(
            RestaurantPhoto.restaurant_id == restaurant_id,
            RestaurantPhoto.is_main == True
        )
    ).update({"is_main": False})
    
    photo.is_main = True
    db.commit()
    db.refresh(photo)
    return photo


# ==================== Review CRUD ====================

def create_review(
    db: Session,
    restaurant_id: int,
    user_id: int,
    review_data: RestaurantReviewCreate
) -> RestaurantReview:
    """Создание отзыва"""
    # Проверяем, есть ли уже отзыв от этого пользователя
    existing_review = db.query(RestaurantReview).filter(
        and_(
            RestaurantReview.restaurant_id == restaurant_id,
            RestaurantReview.user_id == user_id
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
        review = RestaurantReview(
            restaurant_id=restaurant_id,
            user_id=user_id,
            rating=review_data.rating,
            comment=review_data.comment
        )
        db.add(review)
        db.commit()
        db.refresh(review)
    
    # Пересчитываем рейтинг ресторана
    _recalculate_restaurant_rating(db, restaurant_id)
    
    return review


def get_reviews_by_restaurant(
    db: Session,
    restaurant_id: int,
    skip: int = 0,
    limit: int = 50
) -> Tuple[List[RestaurantReview], int]:
    """Получение отзывов по ресторану"""
    query = db.query(RestaurantReview).filter(RestaurantReview.restaurant_id == restaurant_id)
    total = query.count()
    reviews = query.order_by(RestaurantReview.created_at.desc()).offset(skip).limit(limit).all()
    return reviews, total


def update_review(
    db: Session,
    review_id: int,
    user_id: int,
    review_update: RestaurantReviewUpdate
) -> Optional[RestaurantReview]:
    """Обновление отзыва"""
    review = db.query(RestaurantReview).filter(
        and_(
            RestaurantReview.id == review_id,
            RestaurantReview.user_id == user_id
        )
    ).first()
    if not review:
        return None
    
    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)
    
    db.commit()
    db.refresh(review)
    
    # Пересчитываем рейтинг ресторана
    _recalculate_restaurant_rating(db, review.restaurant_id)
    
    return review


def delete_review(db: Session, review_id: int, user_id: int) -> bool:
    """Удаление отзыва"""
    review = db.query(RestaurantReview).filter(
        and_(
            RestaurantReview.id == review_id,
            RestaurantReview.user_id == user_id
        )
    ).first()
    if not review:
        return False
    
    restaurant_id = review.restaurant_id
    db.delete(review)
    db.commit()
    
    # Пересчитываем рейтинг ресторана
    _recalculate_restaurant_rating(db, restaurant_id)
    
    return True


def _recalculate_restaurant_rating(db: Session, restaurant_id: int):
    """Пересчет рейтинга ресторана на основе отзывов"""
    reviews = db.query(RestaurantReview).filter(RestaurantReview.restaurant_id == restaurant_id).all()
    
    if not reviews:
        rating = 0.0
        count = 0
    else:
        rating = sum(r.rating for r in reviews) / len(reviews)
        count = len(reviews)
    
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if restaurant:
        restaurant.rating = round(rating, 2)
        restaurant.reviews_count = count
        db.commit()











