"""
API эндпоинты для автомоек (администраторские)
"""
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_admin_user
from app.services.car_wash_service.crud import (
    create_car_wash,
    get_car_wash_by_id,
    get_car_washes,
    update_car_wash,
    delete_car_wash,
    approve_car_wash,
    reject_car_wash,
    add_car_wash_photo,
    delete_car_wash_photo,
    set_main_photo,
    bulk_update_car_wash_services,
    get_car_wash_services_by_car_wash,
)
from app.schemas.car_wash import (
    CarWashCreate,
    CarWashUpdate,
    CarWashAdminUpdate,
    CarWashResponse,
    CarWashDetailResponse,
    CarWashListResponse,
    CarWashFilter,
    BulkCarWashServiceUpdate,
    CarWashPhotoResponse,
    CarWashStatusEnum,
    CarWashServiceResponse,
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
async def admin_create_car_wash(
    car_wash_data: CarWashCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание новой автомойки (админ, сразу одобрена)"""
    car_wash = create_car_wash(
        db=db,
        car_wash_data=car_wash_data,
        created_by_admin_id=current_user.id
    )
    
    db.refresh(car_wash)
    return CarWashResponse.model_validate(car_wash)


@router.get("/", response_model=CarWashListResponse)
async def admin_list_car_washes(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[CarWashStatusEnum] = Query(None),
    service_type: Optional[str] = Query(None),
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
    search_query: Optional[str] = Query(None)
):
    """Получение списка всех автомоек (включая ожидающие модерации)"""
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
        status=status
    )
    
    car_washes, total = get_car_washes(db, skip=skip, limit=limit, filters=filters)
    
    car_wash_responses = []
    for car_wash in car_washes:
        car_wash_dict = CarWashResponse.model_validate(car_wash).model_dump()
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


@router.get("/{car_wash_id}", response_model=CarWashDetailResponse)
async def admin_get_car_wash(
    car_wash_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение детальной информации об автомойке"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    # Получаем отзывы
    from app.services.car_wash_service.crud import get_reviews_by_car_wash
    reviews, _ = get_reviews_by_car_wash(db, car_wash_id, skip=0, limit=50)
    
    # Преобразуем отзывы с именами пользователей
    from app.services.user_service.crud import get_user_extended_by_id
    review_responses = []
    for review in reviews:
        from app.schemas.car_wash import CarWashReviewResponse
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


@router.put("/{car_wash_id}", response_model=CarWashResponse)
async def admin_update_car_wash(
    car_wash_id: int,
    car_wash_update: CarWashAdminUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление автомойки"""
    car_wash = update_car_wash(db, car_wash_id, car_wash_update)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    db.refresh(car_wash)
    return CarWashResponse.model_validate(car_wash)


@router.delete("/{car_wash_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_car_wash(
    car_wash_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление автомойки"""
    success = delete_car_wash(db, car_wash_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    return None


@router.post("/{car_wash_id}/approve", response_model=CarWashResponse)
async def admin_approve_car_wash(
    car_wash_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Одобрение автомойки"""
    car_wash = approve_car_wash(db, car_wash_id)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    return CarWashResponse.model_validate(car_wash)


@router.post("/{car_wash_id}/reject", response_model=CarWashResponse)
async def admin_reject_car_wash(
    car_wash_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отклонение автомойки"""
    car_wash = reject_car_wash(db, car_wash_id)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    return CarWashResponse.model_validate(car_wash)


@router.post("/{car_wash_id}/photos", response_model=CarWashPhotoResponse, status_code=status.HTTP_201_CREATED)
async def admin_upload_car_wash_photo(
    car_wash_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    is_main: bool = Query(False),
    order: int = Query(0, ge=0)
):
    """Загрузка фотографии для автомойки (админ)"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла. Разрешены: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    photo_url = save_uploaded_photo(file, car_wash_id)
    
    photo = add_car_wash_photo(
        db=db,
        car_wash_id=car_wash_id,
        photo_url=photo_url,
        is_main=is_main,
        order=order,
        uploaded_by_admin_id=current_user.id
    )
    
    return CarWashPhotoResponse.model_validate(photo)


@router.delete("/{car_wash_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_car_wash_photo(
    car_wash_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление фотографии автомойки (админ)"""
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
    
    delete_car_wash_photo(db, photo_id)
    return None


@router.post("/{car_wash_id}/photos/{photo_id}/set-main", response_model=CarWashPhotoResponse)
async def admin_set_main_photo(
    car_wash_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Установка главной фотографии (админ)"""
    photo = set_main_photo(db, car_wash_id, photo_id)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена"
        )
    
    return CarWashPhotoResponse.model_validate(photo)


@router.post("/{car_wash_id}/services", response_model=List[CarWashServiceResponse])
async def admin_update_car_wash_services(
    car_wash_id: int,
    services: BulkCarWashServiceUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление услуг автомойки (админ)"""
    car_wash = get_car_wash_by_id(db, car_wash_id)
    if not car_wash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомойка не найдена"
        )
    
    updated_services = bulk_update_car_wash_services(
        db=db,
        car_wash_id=car_wash_id,
        services=services.services,
        updated_by_admin_id=current_user.id
    )
    
    return [CarWashServiceResponse.model_validate(s) for s in updated_services]











