"""
API эндпоинты для ресторанов (администраторские)
"""
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_admin_user
from app.services.restaurant_service.crud import (
    create_restaurant,
    get_restaurant_by_id,
    get_restaurants,
    update_restaurant,
    delete_restaurant,
    approve_restaurant,
    reject_restaurant,
    add_restaurant_photo,
    delete_restaurant_photo,
    set_main_photo,
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
    RestaurantUpdate,
    RestaurantAdminUpdate,
    RestaurantResponse,
    RestaurantDetailResponse,
    RestaurantListResponse,
    RestaurantFilter,
    RestaurantPhotoResponse,
    RestaurantStatusEnum,
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
async def admin_create_restaurant(
    restaurant_data: RestaurantCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание нового ресторана (админ, сразу одобрен)"""
    restaurant = create_restaurant(
        db=db,
        restaurant_data=restaurant_data,
        created_by_admin_id=current_user.id
    )
    
    db.refresh(restaurant)
    return RestaurantResponse.model_validate(restaurant)


@router.get("/", response_model=RestaurantListResponse)
async def admin_list_restaurants(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[RestaurantStatusEnum] = Query(None),
    cuisine_type: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    min_average_check: Optional[float] = Query(None, gt=0),
    max_average_check: Optional[float] = Query(None, gt=0),
    is_24_7: Optional[bool] = Query(None),
    has_promotions: Optional[bool] = Query(None),
    has_booking: Optional[bool] = Query(None),
    has_delivery: Optional[bool] = Query(None),
    has_parking: Optional[bool] = Query(None),
    has_wifi: Optional[bool] = Query(None),
    search_query: Optional[str] = Query(None)
):
    """Получение списка всех ресторанов (включая ожидающие модерации)"""
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
        status=status
    )
    
    restaurants, total = get_restaurants(db, skip=skip, limit=limit, filters=filters)
    
    restaurant_responses = []
    for restaurant in restaurants:
        restaurant_dict = RestaurantResponse.model_validate(restaurant).model_dump()
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


@router.get("/{restaurant_id}", response_model=RestaurantDetailResponse)
async def admin_get_restaurant(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение детальной информации о ресторане"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    # Получаем отзывы
    from app.services.restaurant_service.crud import get_reviews_by_restaurant
    reviews, _ = get_reviews_by_restaurant(db, restaurant_id, skip=0, limit=50)
    
    # Преобразуем отзывы с именами пользователей
    from app.services.user_service.crud import get_user_extended_by_id
    review_responses = []
    for review in reviews:
        from app.schemas.restaurant import RestaurantReviewResponse
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


@router.put("/{restaurant_id}", response_model=RestaurantResponse)
async def admin_update_restaurant(
    restaurant_id: int,
    restaurant_update: RestaurantAdminUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление ресторана"""
    restaurant = update_restaurant(db, restaurant_id, restaurant_update)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    db.refresh(restaurant)
    return RestaurantResponse.model_validate(restaurant)


@router.delete("/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_restaurant(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление ресторана"""
    success = delete_restaurant(db, restaurant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    return None


@router.post("/{restaurant_id}/approve", response_model=RestaurantResponse)
async def admin_approve_restaurant(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Одобрение ресторана"""
    restaurant = approve_restaurant(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    return RestaurantResponse.model_validate(restaurant)


@router.post("/{restaurant_id}/reject", response_model=RestaurantResponse)
async def admin_reject_restaurant(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отклонение ресторана"""
    restaurant = reject_restaurant(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    return RestaurantResponse.model_validate(restaurant)


@router.post("/{restaurant_id}/photos", response_model=RestaurantPhotoResponse, status_code=status.HTTP_201_CREATED)
async def admin_upload_restaurant_photo(
    restaurant_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    is_main: bool = Query(False),
    order: int = Query(0, ge=0)
):
    """Загрузка фотографии для ресторана (админ)"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
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
        uploaded_by_admin_id=current_user.id
    )
    
    return RestaurantPhotoResponse.model_validate(photo)


@router.delete("/{restaurant_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_restaurant_photo(
    restaurant_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление фотографии ресторана (админ)"""
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
    
    delete_restaurant_photo(db, photo_id)
    return None


@router.post("/{restaurant_id}/photos/{photo_id}/set-main", response_model=RestaurantPhotoResponse)
async def admin_set_main_photo(
    restaurant_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Установка главной фотографии (админ)"""
    photo = set_main_photo(db, restaurant_id, photo_id)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена"
        )
    
    return RestaurantPhotoResponse.model_validate(photo)


# ==================== Menu Categories (Admin) ====================

@router.post("/{restaurant_id}/menu/categories", response_model=MenuCategoryResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_menu_category(
    restaurant_id: int,
    category_data: MenuCategoryCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание категории меню (админ)"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    category = create_menu_category(db, restaurant_id, category_data)
    return MenuCategoryResponse.model_validate(category)


@router.put("/{restaurant_id}/menu/categories/{category_id}", response_model=MenuCategoryResponse)
async def admin_update_menu_category(
    restaurant_id: int,
    category_id: int,
    category_update: MenuCategoryUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление категории меню (админ)"""
    category = update_menu_category(db, category_id, category_update)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    
    return MenuCategoryResponse.model_validate(category)


@router.delete("/{restaurant_id}/menu/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_menu_category(
    restaurant_id: int,
    category_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление категории меню (админ)"""
    success = delete_menu_category(db, category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена"
        )
    return None


# ==================== Menu Items (Admin) ====================

@router.post("/{restaurant_id}/menu/categories/{category_id}/items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_menu_item(
    restaurant_id: int,
    category_id: int,
    item_data: MenuItemCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание блюда в меню (админ)"""
    restaurant = get_restaurant_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресторан не найден"
        )
    
    item = create_menu_item(db, category_id, restaurant_id, item_data)
    return MenuItemResponse.model_validate(item)


@router.put("/{restaurant_id}/menu/items/{item_id}", response_model=MenuItemResponse)
async def admin_update_menu_item(
    restaurant_id: int,
    item_id: int,
    item_update: MenuItemUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление блюда (админ)"""
    item = update_menu_item(db, item_id, item_update)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Блюдо не найдено"
        )
    
    return MenuItemResponse.model_validate(item)


@router.delete("/{restaurant_id}/menu/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_menu_item(
    restaurant_id: int,
    item_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление блюда (админ)"""
    success = delete_menu_item(db, item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Блюдо не найдено"
        )
    return None











