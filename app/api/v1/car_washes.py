"""
API эндпоинты для автомоек (пользовательские)
"""
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.car_wash_service.crud import (
    create_car_wash,
    get_car_wash_by_id,
    get_car_washes,
    create_review,
    get_reviews_by_car_wash,
    update_review,
    delete_review,
    add_car_wash_photo,
    get_car_wash_photos,
    delete_car_wash_photo,
    create_or_update_car_wash_service,
    bulk_update_car_wash_services,
    get_car_wash_services_by_car_wash,
    delete_car_wash_service,
)
from app.schemas.car_wash import (
    CarWashCreate,
    CarWashResponse,
    CarWashDetailResponse,
    CarWashListResponse,
    CarWashFilter,
    CarWashServiceCreate,
    CarWashServiceResponse,
    CarWashReviewCreate,
    CarWashReviewResponse,
    CarWashReviewUpdate,
    CarWashPhotoResponse,
    BulkCarWashServiceUpdate,
)
from app.core.config import settings
from app.models.car_wash import CarWashStatus

router = APIRouter()

# Директория для загрузки фотографий автомоек
CAR_WASH_PHOTOS_DIR = Path(settings.UPLOAD_DIR) / "car_washes"
CAR_WASH_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_photo(file: UploadFile, car_wash_id: int) -> str:
    """Сохранение загруженной фотографии и возврат URL"""
    file_extension = Path(file.filename).suffix if file.filename else ".jpg"
    unique_filename = f"{car_wash_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = CAR_WASH_PHOTOS_DIR / unique_filename
    
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    # Возвращаем URL
    relative_path = f"uploads/car_washes/{unique_filename}"
    return f"{settings.BASE_URL}/{relative_path}"


@router.post("/", response_model=CarWashResponse, status_code=status.HTTP_201_CREATED)
async def create_car_wash_endpoint(
    car_wash_data: CarWashCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание новой автомойки (требует модерации)"""
    car_wash = create_car_wash(
        db=db,
        car_wash_data=car_wash_data,
        created_by_user_id=current_user.id
    )
    
    db.refresh(car_wash)
    return CarWashResponse.model_validate(car_wash)


@router.get("/", response_model=CarWashListResponse)
async def list_car_washes(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service_type: Optional[str] = Query(None, description="Тип услуги"),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    min_price: Optional[float] = Query(None, gt=0),
    max_price: Optional[float] = Query(None, gt=0),
    is_24_7: Optional[bool] = Query(None),
    has_promotions: Optional[bool] = Query(None),
    has_parking: Optional[bool] = Query(None),
    has_waiting_room: Optional[bool] = Query(None),
    has_cafe: Optional[bool] = Query(None),
    accepts_cards: Optional[bool] = Query(None),
    has_vacuum: Optional[bool] = Query(None),
    has_drying: Optional[bool] = Query(None),
    has_self_service: Optional[bool] = Query(None),
    search_query: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: Optional[float] = Query(None, gt=0)
):
    """Получение списка автомоек с фильтрацией"""
    filters = CarWashFilter(
        service_type=service_type,
        min_rating=min_rating,
        min_price=min_price,
        max_price=max_price,
        is_24_7=is_24_7,
        has_promotions=has_promotions,
        has_parking=has_parking,
        has_waiting_room=has_waiting_room,
        has_cafe=has_cafe,
        accepts_cards=accepts_cards,
        has_vacuum=has_vacuum,
        has_drying=has_drying,
        has_self_service=has_self_service,
        search_query=search_query,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )
    
    car_washes, total = get_car_washes(db, skip=skip, limit=limit, filters=filters)
    
    # Преобразуем в ответы
    car_wash_responses = []
    for car_wash in car_washes:
        car_wash_dict = CarWashResponse.model_validate(car_wash).model_dump()
        # Находим главную фотографию
        main_photo = next((p for p in car_wash.photos if p.is_main), None)
        if main_photo:
            car_wash_dict["main_photo"] = main_photo.photo_url
        car_wash_responses.append(CarWashResponse(**car_wash_dict))
    
    return CarWashListResponse(
        car_washes=car_wash_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/favorites", response_model=CarWashListResponse)
async def get_favorite_car_washes(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """Получение списка избранных автомоек пользователя"""
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.favorites_service.crud import get_favorites_by_user_id

    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )

    favorites_list = get_favorites_by_user_id(db, user_extended.id, favorite_type="car_wash")
    car_wash_responses = []
    for fav in favorites_list:
        car_wash = get_car_wash_by_id(db, fav.place_id)
        if car_wash and car_wash.status == CarWashStatus.APPROVED:
            car_wash_dict = CarWashResponse.model_validate(car_wash).model_dump()
            main_photo = next((p for p in car_wash.photos if p.is_main), None)
            if main_photo:
                car_wash_dict["main_photo"] = main_photo.photo_url
            car_wash_responses.append(CarWashResponse(**car_wash_dict))

    total = len(car_wash_responses)
    paginated = car_wash_responses[skip : skip + limit]

    return CarWashListResponse(
        car_washes=paginated,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/{car_wash_id}/favorite", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_car_wash_to_favorites(
    car_wash_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Добавить автомойку в избранное"""
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.favorites_service.crud import create_favorite
    from app.schemas.user_extended import UserFavoriteCreate

    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash or car_wash.status != CarWashStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )

    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )

    favorite_data = UserFavoriteCreate(favorite_type="car_wash", place_id=car_wash_id)
    created_favorite = create_favorite(db, user_extended.id, favorite_data)
    return {"message": "Добавлено в избранное", "id": created_favorite.id}


@router.delete("/{car_wash_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_car_wash_from_favorites(
    car_wash_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удалить автомойку из избранного"""
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.favorites_service.crud import delete_favorite

    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )

    deleted = delete_favorite(db, user_extended.id, "car_wash", car_wash_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не была в избранном"
        )


@router.get("/{car_wash_id}", response_model=CarWashDetailResponse)
async def get_car_wash(
    car_wash_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение детальной информации об автомойке"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    if car_wash.status != CarWashStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    # Получаем отзывы
    reviews, _ = get_reviews_by_car_wash(db, car_wash_id, skip=0, limit=50)
    
    # Преобразуем отзывы с именами пользователей
    from app.services.user_service.crud import get_user_extended_by_id
    review_responses = []
    for review in reviews:
        review_dict = CarWashReviewResponse.model_validate(review).model_dump()
        user_extended = get_user_extended_by_id(db, review.user_id)
        if user_extended:
            review_dict["user_name"] = user_extended.name
        review_responses.append(CarWashReviewResponse(**review_dict))
    
    car_wash_dict = CarWashDetailResponse.model_validate(car_wash).model_dump()
    car_wash_dict["reviews"] = review_responses
    
    # Находим главную фотографию
    main_photo = next((p for p in car_wash.photos if p.is_main), None)
    if main_photo:
        car_wash_dict["main_photo"] = main_photo.photo_url
    
    return CarWashDetailResponse(**car_wash_dict)


@router.post("/{car_wash_id}/photos", response_model=CarWashPhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_car_wash_photo(
    car_wash_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    is_main: bool = Query(False),
    order: int = Query(0, ge=0)
):
    """Загрузка фотографии для автомойки"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    # Проверяем права: только создатель или админ может добавлять фото
    if car_wash.created_by_user_id != current_user.id and not current_user.is_admin:
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
    photo_url = save_uploaded_photo(file, car_wash_id)
    
    # Добавляем в БД
    photo = add_car_wash_photo(
        db=db,
        car_wash_id=car_wash_id,
        photo_url=photo_url,
        is_main=is_main,
        order=order,
        uploaded_by_user_id=current_user.id if not current_user.is_admin else None,
        uploaded_by_admin_id=current_user.id if current_user.is_admin else None
    )
    
    return CarWashPhotoResponse.model_validate(photo)


@router.delete("/{car_wash_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car_wash_photo_endpoint(
    car_wash_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление фотографии автомойки"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    photo = next((p for p in car_wash.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена"
        )
    
    # Проверяем права
    if car_wash.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления фотографий"
        )
    
    delete_car_wash_photo(db, photo_id)
    return None


@router.post("/{car_wash_id}/services", response_model=List[CarWashServiceResponse])
async def update_car_wash_services(
    car_wash_id: int,
    services: BulkCarWashServiceUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление услуг автомойки"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    # Проверяем права: только создатель или админ может обновлять услуги
    if car_wash.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для обновления услуг"
        )
    
    updated_services = bulk_update_car_wash_services(
        db=db,
        car_wash_id=car_wash_id,
        services=services.services,
        updated_by_user_id=current_user.id if not current_user.is_admin else None,
        updated_by_admin_id=current_user.id if current_user.is_admin else None
    )
    
    return [CarWashServiceResponse.model_validate(s) for s in updated_services]


@router.post("/{car_wash_id}/reviews", response_model=CarWashReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_car_wash_review(
    car_wash_id: int,
    review_data: CarWashReviewCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание отзыва об автомойке"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash or car_wash.status != CarWashStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    review = create_review(
        db=db,
        car_wash_id=car_wash_id,
        user_id=current_user.id,
        review_data=review_data
    )
    
    # Получаем имя пользователя
    from app.services.user_service.crud import get_user_extended_by_id
    user_extended = get_user_extended_by_id(db, current_user.id)
    review_dict = CarWashReviewResponse.model_validate(review).model_dump()
    if user_extended:
        review_dict["user_name"] = user_extended.name
    
    return CarWashReviewResponse(**review_dict)


@router.put("/{car_wash_id}/reviews/{review_id}", response_model=CarWashReviewResponse)
async def update_car_wash_review(
    car_wash_id: int,
    review_id: int,
    review_update: CarWashReviewUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление отзыва об автомойке"""
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
    review_dict = CarWashReviewResponse.model_validate(review).model_dump()
    if user_extended:
        review_dict["user_name"] = user_extended.name
    
    return CarWashReviewResponse(**review_dict)


@router.delete("/{car_wash_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car_wash_review(
    car_wash_id: int,
    review_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление отзыва об автомойке"""
    success = delete_review(db, review_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )
    return None











