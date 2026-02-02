"""
API эндпоинты для ресторанов (пользовательские)
"""
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.restaurant_service.crud import (
    create_restaurant,
    get_restaurant_by_id,
    get_restaurants,
    create_review,
    get_reviews_by_restaurant,
    update_review,
    delete_review,
    add_restaurant_photo,
    get_restaurant_photos,
    delete_restaurant_photo,
    create_menu_category,
    get_menu_categories_by_restaurant,
    update_menu_category,
    delete_menu_category,
    create_menu_item,
    get_menu_items_by_category,
    update_menu_item,
    delete_menu_item,
)
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantResponse,
    RestaurantDetailResponse,
    RestaurantListResponse,
    RestaurantFilter,
    RestaurantReviewCreate,
    RestaurantReviewResponse,
    RestaurantReviewUpdate,
    RestaurantPhotoResponse,
    MenuCategoryCreate,
    MenuCategoryResponse,
    MenuCategoryUpdate,
    MenuItemCreate,
    MenuItemResponse,
    MenuItemUpdate,
)
from app.core.config import settings
from app.models.restaurant import RestaurantStatus

router = APIRouter()

# Директория для загрузки фотографий ресторанов
RESTAURANT_PHOTOS_DIR = Path(settings.UPLOAD_DIR) / "restaurants"
RESTAURANT_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Директория для загрузки фотографий блюд
MENU_ITEM_PHOTOS_DIR = Path(settings.UPLOAD_DIR) / "restaurants" / "menu_items"
MENU_ITEM_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_photo(file: UploadFile, restaurant_id: int, is_menu_item: bool = False) -> str:
    """Сохранение загруженной фотографии и возврат URL"""
    file_extension = Path(file.filename).suffix if file.filename else ".jpg"
    unique_filename = f"{restaurant_id}_{uuid.uuid4().hex}{file_extension}"
    
    if is_menu_item:
        file_path = MENU_ITEM_PHOTOS_DIR / unique_filename
        relative_path = f"uploads/restaurants/menu_items/{unique_filename}"
    else:
        file_path = RESTAURANT_PHOTOS_DIR / unique_filename
        relative_path = f"uploads/restaurants/{unique_filename}"
    
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    return f"{settings.BASE_URL}/{relative_path}"


@router.post("/", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
async def create_restaurant_endpoint(
    restaurant_data: RestaurantCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание нового ресторана (требует модерации)"""
    restaurant = create_restaurant(
        db=db,
        restaurant_data=restaurant_data,
        created_by_user_id=current_user.id
    )
    
    db.refresh(restaurant)
    return RestaurantResponse.model_validate(restaurant)


@router.get("/", response_model=RestaurantListResponse)
async def list_restaurants(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    cuisine_type: Optional[str] = Query(None, description="Тип кухни"),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    min_average_check: Optional[float] = Query(None, gt=0),
    max_average_check: Optional[float] = Query(None, gt=0),
    is_24_7: Optional[bool] = Query(None),
    has_promotions: Optional[bool] = Query(None),
    has_booking: Optional[bool] = Query(None),
    has_delivery: Optional[bool] = Query(None),
    has_parking: Optional[bool] = Query(None),
    has_wifi: Optional[bool] = Query(None),
    search_query: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: Optional[float] = Query(None, gt=0)
):
    """Получение списка ресторанов с фильтрацией"""
    filters = RestaurantFilter(
        cuisine_type=cuisine_type,
        min_rating=min_rating,
        min_average_check=min_average_check,
        max_average_check=max_average_check,
        is_24_7=is_24_7,
        has_promotions=has_promotions,
        has_booking=has_booking,
        has_delivery=has_delivery,
        has_parking=has_parking,
        has_wifi=has_wifi,
        search_query=search_query,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )
    
    restaurants, total = get_restaurants(db, skip=skip, limit=limit, filters=filters)
    
    # Преобразуем в ответы
    restaurant_responses = []
    for restaurant in restaurants:
        restaurant_dict = RestaurantResponse.model_validate(restaurant).model_dump()
        # Находим главную фотографию
        main_photo = next((p for p in restaurant.photos if p.is_main), None)
        if main_photo:
            restaurant_dict["main_photo"] = main_photo.photo_url
        restaurant_responses.append(RestaurantResponse(**restaurant_dict))
    
    return RestaurantListResponse(
        restaurants=restaurant_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/favorites", response_model=RestaurantListResponse)
async def get_favorite_restaurants(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """Получение списка избранных ресторанов пользователя"""
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.favorites_service.crud import get_favorites_by_user_id

    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )

    favorites_list = get_favorites_by_user_id(db, user_extended.id, favorite_type="restaurant")
    restaurant_responses = []
    for fav in favorites_list:
        restaurant = get_restaurant_by_id(db, fav.place_id)
        if restaurant and restaurant.status == RestaurantStatus.APPROVED:
            restaurant_dict = RestaurantResponse.model_validate(restaurant).model_dump()
            main_photo = next((p for p in restaurant.photos if p.is_main), None)
            if main_photo:
                restaurant_dict["main_photo"] = main_photo.photo_url
            restaurant_responses.append(RestaurantResponse(**restaurant_dict))

    total = len(restaurant_responses)
    paginated = restaurant_responses[skip : skip + limit]

    return RestaurantListResponse(
        restaurants=paginated,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/{restaurant_id}/favorite", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_restaurant_to_favorites(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Добавить ресторан в избранное"""
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.favorites_service.crud import create_favorite
    from app.schemas.user_extended import UserFavoriteCreate

    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant or restaurant.status != RestaurantStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )

    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )

    favorite_data = UserFavoriteCreate(favorite_type="restaurant", place_id=restaurant_id)
    created_favorite = create_favorite(db, user_extended.id, favorite_data)
    return {"message": "Добавлено в избранное", "id": created_favorite.id}


@router.delete("/{restaurant_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_restaurant_from_favorites(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удалить ресторан из избранного"""
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.favorites_service.crud import delete_favorite

    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )

    deleted = delete_favorite(db, user_extended.id, "restaurant", restaurant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не был в избранном"
        )


@router.get("/{restaurant_id}", response_model=RestaurantDetailResponse)
async def get_restaurant(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение детальной информации о ресторане"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    if restaurant.status != RestaurantStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    # Получаем отзывы
    reviews, _ = get_reviews_by_restaurant(db, restaurant_id, skip=0, limit=50)
    
    # Преобразуем отзывы с именами пользователей
    from app.services.user_service.crud import get_user_extended_by_id
    review_responses = []
    for review in reviews:
        review_dict = RestaurantReviewResponse.model_validate(review).model_dump()
        user_extended = get_user_extended_by_id(db, review.user_id)
        if user_extended:
            review_dict["user_name"] = user_extended.name
        review_responses.append(RestaurantReviewResponse(**review_dict))
    
    restaurant_dict = RestaurantDetailResponse.model_validate(restaurant).model_dump()
    restaurant_dict["reviews"] = review_responses
    
    # Находим главную фотографию
    main_photo = next((p for p in restaurant.photos if p.is_main), None)
    if main_photo:
        restaurant_dict["main_photo"] = main_photo.photo_url
    
    return RestaurantDetailResponse(**restaurant_dict)


@router.post("/{restaurant_id}/photos", response_model=RestaurantPhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_restaurant_photo(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    is_main: bool = Query(False),
    order: int = Query(0, ge=0)
):
    """Загрузка фотографии для ресторана"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    # Проверяем права: только создатель или админ может добавлять фото
    if restaurant.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для добавления фотографий"
        )
    
    # Проверяем тип файла
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла. Разрешены: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    # Сохраняем файл
    photo_url = save_uploaded_photo(file, restaurant_id, is_menu_item=False)
    
    # Добавляем в БД
    photo = add_restaurant_photo(
        db=db,
        restaurant_id=restaurant_id,
        photo_url=photo_url,
        is_main=is_main,
        order=order,
        uploaded_by_user_id=current_user.id if not current_user.is_admin else None,
        uploaded_by_admin_id=current_user.id if current_user.is_admin else None
    )
    
    return RestaurantPhotoResponse.model_validate(photo)


@router.delete("/{restaurant_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_restaurant_photo_endpoint(
    restaurant_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление фотографии ресторана"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    photo = next((p for p in restaurant.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена"
        )
    
    # Проверяем права
    if restaurant.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления фотографий"
        )
    
    delete_restaurant_photo(db, photo_id)
    return None


# ==================== Menu Categories ====================

@router.post("/{restaurant_id}/menu/categories", response_model=MenuCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_category_endpoint(
    restaurant_id: int,
    category_data: MenuCategoryCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание категории меню"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    # Проверяем права
    if restaurant.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для управления меню"
        )
    
    category = create_menu_category(db, restaurant_id, category_data)
    return MenuCategoryResponse.model_validate(category)


@router.get("/{restaurant_id}/menu/categories", response_model=List[MenuCategoryResponse])
async def get_menu_categories(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение всех категорий меню ресторана"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant or restaurant.status != RestaurantStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    categories = get_menu_categories_by_restaurant(db, restaurant_id)
    return [MenuCategoryResponse.model_validate(cat) for cat in categories]


@router.put("/{restaurant_id}/menu/categories/{category_id}", response_model=MenuCategoryResponse)
async def update_menu_category_endpoint(
    restaurant_id: int,
    category_id: int,
    category_update: MenuCategoryUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление категории меню"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    # Проверяем права
    if restaurant.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для управления меню"
        )
    
    category = update_menu_category(db, category_id, category_update)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    return MenuCategoryResponse.model_validate(category)


@router.delete("/{restaurant_id}/menu/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_category_endpoint(
    restaurant_id: int,
    category_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление категории меню"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    # Проверяем права
    if restaurant.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для управления меню"
        )
    
    success = delete_menu_category(db, category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    return None


# ==================== Menu Items ====================

@router.post("/{restaurant_id}/menu/categories/{category_id}/items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item_endpoint(
    restaurant_id: int,
    category_id: int,
    item_data: MenuItemCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание блюда в меню"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    # Проверяем права
    if restaurant.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для управления меню"
        )
    
    item = create_menu_item(db, category_id, restaurant_id, item_data)
    return MenuItemResponse.model_validate(item)


@router.get("/{restaurant_id}/menu/categories/{category_id}/items", response_model=List[MenuItemResponse])
async def get_menu_items(
    restaurant_id: int,
    category_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение всех блюд категории"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant or restaurant.status != RestaurantStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    items = get_menu_items_by_category(db, category_id)
    return [MenuItemResponse.model_validate(item) for item in items]


@router.put("/{restaurant_id}/menu/items/{item_id}", response_model=MenuItemResponse)
async def update_menu_item_endpoint(
    restaurant_id: int,
    item_id: int,
    item_update: MenuItemUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление блюда"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    # Проверяем права
    if restaurant.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для управления меню"
        )
    
    item = update_menu_item(db, item_id, item_update)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Блюдо не найдено"
        )
    
    return MenuItemResponse.model_validate(item)


@router.delete("/{restaurant_id}/menu/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item_endpoint(
    restaurant_id: int,
    item_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление блюда"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    # Проверяем права
    if restaurant.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для управления меню"
        )
    
    success = delete_menu_item(db, item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Блюдо не найдено"
        )
    return None


# ==================== Reviews ====================

@router.post("/{restaurant_id}/reviews", response_model=RestaurantReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_restaurant_review(
    restaurant_id: int,
    review_data: RestaurantReviewCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание отзыва о ресторане"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant or restaurant.status != RestaurantStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    review = create_review(
        db=db,
        restaurant_id=restaurant_id,
        user_id=current_user.id,
        review_data=review_data
    )
    
    # Получаем имя пользователя
    from app.services.user_service.crud import get_user_extended_by_id
    user_extended = get_user_extended_by_id(db, current_user.id)
    review_dict = RestaurantReviewResponse.model_validate(review).model_dump()
    if user_extended:
        review_dict["user_name"] = user_extended.name
    
    return RestaurantReviewResponse(**review_dict)


@router.put("/{restaurant_id}/reviews/{review_id}", response_model=RestaurantReviewResponse)
async def update_restaurant_review(
    restaurant_id: int,
    review_id: int,
    review_update: RestaurantReviewUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление отзыва о ресторане"""
    review = update_review(
        db=db,
        review_id=review_id,
        user_id=current_user.id,
        review_update=review_update
    )
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )
    
    # Получаем имя пользователя
    from app.services.user_service.crud import get_user_extended_by_id
    user_extended = get_user_extended_by_id(db, current_user.id)
    review_dict = RestaurantReviewResponse.model_validate(review).model_dump()
    if user_extended:
        review_dict["user_name"] = user_extended.name
    
    return RestaurantReviewResponse(**review_dict)


@router.delete("/{restaurant_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_restaurant_review(
    restaurant_id: int,
    review_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление отзыва о ресторане"""
    success = delete_review(db, review_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )
    return None

