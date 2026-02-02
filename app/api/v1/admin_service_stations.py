"""
API эндпоинты для станций технического обслуживания (СТО) (администраторские)
"""
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_admin_user
from app.services.service_station_service.crud import (
    create_service_station,
    get_service_station_by_id,
    get_service_stations,
    update_service_station,
    delete_service_station,
    approve_service_station,
    reject_service_station,
    add_service_station_photo,
    delete_service_station_photo,
    set_main_photo,
    bulk_update_service_prices,
    get_service_prices_by_station,
)
from app.schemas.service_station import (
    ServiceStationCreate,
    ServiceStationUpdate,
    ServiceStationAdminUpdate,
    ServiceStationResponse,
    ServiceStationDetailResponse,
    ServiceStationListResponse,
    ServiceStationFilter,
    BulkServicePriceUpdate,
    ServiceStationPhotoResponse,
    ServiceStationStatusEnum,
    ServicePriceResponse,
)
from app.core.config import settings
from app.models.service_station import ServiceStationStatus

router = APIRouter()

# Директория для загрузки фотографий СТО
SERVICE_STATION_PHOTOS_DIR = Path(settings.UPLOAD_DIR) / "service_stations"
SERVICE_STATION_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_photo(file: UploadFile, station_id: int) -> str:
    """Сохранение загруженной фотографии и возврат URL"""
    file_extension = Path(file.filename).suffix if file.filename else ".jpg"
    unique_filename = f"{station_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = SERVICE_STATION_PHOTOS_DIR / unique_filename
    
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    # Возвращаем URL
    relative_path = f"uploads/service_stations/{unique_filename}"
    return f"{settings.BASE_URL}/{relative_path}"


@router.post("/", response_model=ServiceStationResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_service_station(
    station_data: ServiceStationCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание новой СТО (админ, сразу одобрена)"""
    station = create_service_station(
        db=db,
        station_data=station_data,
        created_by_admin_id=current_user.id
    )
    
    db.refresh(station)
    return ServiceStationResponse.model_validate(station)


@router.get("/", response_model=ServiceStationListResponse)
async def admin_list_service_stations(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[ServiceStationStatusEnum] = Query(None),
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
    search_query: Optional[str] = Query(None)
):
    """Получение списка всех СТО (включая ожидающие модерации)"""
    filters = ServiceStationFilter(
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
        search_query=search_query,
        status=status
    )
    
    stations, total = get_service_stations(db, skip=skip, limit=limit, filters=filters)
    
    station_responses = []
    for station in stations:
        station_dict = ServiceStationResponse.model_validate(station).model_dump()
        main_photo = next((p for p in station.photos if p.is_main), None)
        if main_photo:
            station_dict["main_photo"] = main_photo.photo_url
        station_responses.append(ServiceStationResponse(**station_dict))
    
    return ServiceStationListResponse(
        service_stations=station_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{station_id}", response_model=ServiceStationDetailResponse)
async def admin_get_service_station(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение детальной информации о СТО"""
    station = get_service_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="СТО не найдена"
        )
    
    # Получаем отзывы
    from app.services.service_station_service.crud import get_reviews_by_station
    reviews, _ = get_reviews_by_station(db, station_id, skip=0, limit=50)
    
    # Преобразуем отзывы с именами пользователей
    from app.services.user_service.crud import get_user_extended_by_id
    review_responses = []
    for review in reviews:
        from app.schemas.service_station import ServiceStationReviewResponse
        review_dict = ServiceStationReviewResponse.model_validate(review).model_dump()
        user_extended = get_user_extended_by_id(db, review.user_id)
        if user_extended:
            review_dict["user_name"] = user_extended.name
        review_responses.append(ServiceStationReviewResponse(**review_dict))
    
    station_dict = ServiceStationDetailResponse.model_validate(station).model_dump()
    station_dict["reviews"] = review_responses
    
    # Находим главную фотографию
    main_photo = next((p for p in station.photos if p.is_main), None)
    if main_photo:
        station_dict["main_photo"] = main_photo.photo_url
    
    return ServiceStationDetailResponse(**station_dict)


@router.put("/{station_id}", response_model=ServiceStationResponse)
async def admin_update_service_station(
    station_id: int,
    station_update: ServiceStationAdminUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление СТО"""
    station = update_service_station(db, station_id, station_update)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="СТО не найдена"
        )
    
    db.refresh(station)
    return ServiceStationResponse.model_validate(station)


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_service_station(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление СТО"""
    success = delete_service_station(db, station_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="СТО не найдена"
        )
    return None


@router.post("/{station_id}/approve", response_model=ServiceStationResponse)
async def admin_approve_service_station(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Одобрение СТО"""
    station = approve_service_station(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="СТО не найдена"
        )
    
    return ServiceStationResponse.model_validate(station)


@router.post("/{station_id}/reject", response_model=ServiceStationResponse)
async def admin_reject_service_station(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отклонение СТО"""
    station = reject_service_station(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="СТО не найдена"
        )
    
    return ServiceStationResponse.model_validate(station)


@router.post("/{station_id}/photos", response_model=ServiceStationPhotoResponse, status_code=status.HTTP_201_CREATED)
async def admin_upload_service_station_photo(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    is_main: bool = Query(False),
    order: int = Query(0, ge=0)
):
    """Загрузка фотографии для СТО (админ)"""
    station = get_service_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="СТО не найдена"
        )
    
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла. Разрешены: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    photo_url = save_uploaded_photo(file, station_id)
    
    photo = add_service_station_photo(
        db=db,
        station_id=station_id,
        photo_url=photo_url,
        is_main=is_main,
        order=order,
        uploaded_by_admin_id=current_user.id
    )
    
    return ServiceStationPhotoResponse.model_validate(photo)


@router.delete("/{station_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_service_station_photo(
    station_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление фотографии СТО (админ)"""
    station = get_service_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="СТО не найдена"
        )
    
    photo = next((p for p in station.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена"
        )
    
    delete_service_station_photo(db, photo_id)
    return None


@router.post("/{station_id}/photos/{photo_id}/set-main", response_model=ServiceStationPhotoResponse)
async def admin_set_main_photo(
    station_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Установка главной фотографии (админ)"""
    photo = set_main_photo(db, station_id, photo_id)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена"
        )
    
    return ServiceStationPhotoResponse.model_validate(photo)


@router.post("/{station_id}/service-prices", response_model=List[ServicePriceResponse])
async def admin_update_service_prices(
    station_id: int,
    prices: BulkServicePriceUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление цен на услуги для СТО (админ)"""
    station = get_service_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="СТО не найдена"
        )
    
    updated_prices = bulk_update_service_prices(
        db=db,
        station_id=station_id,
        prices=prices.service_prices,
        updated_by_admin_id=current_user.id
    )
    
    return [ServicePriceResponse.model_validate(p) for p in updated_prices]











