"""
API эндпоинты для электрозаправок (администраторские)
"""
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_admin_user
from app.services.electric_station_service.crud import (
    create_electric_station,
    get_electric_station_by_id,
    get_electric_stations,
    update_electric_station,
    delete_electric_station,
    approve_electric_station,
    reject_electric_station,
    add_electric_station_photo,
    delete_electric_station_photo,
    set_main_photo,
    bulk_update_charging_points,
    get_charging_points_by_station,
)
from app.schemas.electric_station import (
    ElectricStationCreate,
    ElectricStationUpdate,
    ElectricStationAdminUpdate,
    ElectricStationResponse,
    ElectricStationDetailResponse,
    ElectricStationListResponse,
    ElectricStationFilter,
    BulkChargingPointUpdate,
    ElectricStationPhotoResponse,
    ChargingPointResponse,
    ElectricStationStatusEnum,
)
from app.core.config import settings
from app.models.electric_station import ElectricStationStatus

router = APIRouter()

# Директория для загрузки фотографий электрозаправок
ELECTRIC_STATION_PHOTOS_DIR = Path(settings.UPLOAD_DIR) / "electric_stations"
ELECTRIC_STATION_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_photo(file: UploadFile, station_id: int) -> str:
    """Сохранение загруженной фотографии и возврат URL"""
    file_extension = Path(file.filename).suffix if file.filename else ".jpg"
    unique_filename = f"{station_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = ELECTRIC_STATION_PHOTOS_DIR / unique_filename
    
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    # Возвращаем URL
    relative_path = f"uploads/electric_stations/{unique_filename}"
    return f"{settings.BASE_URL}/{relative_path}"


@router.post("/", response_model=ElectricStationResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_electric_station(
    station_data: ElectricStationCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание новой электрозаправки (админ, сразу одобрена)"""
    station = create_electric_station(
        db=db,
        station_data=station_data,
        created_by_admin_id=current_user.id
    )
    
    db.refresh(station)
    return ElectricStationResponse.model_validate(station)


@router.get("/", response_model=ElectricStationListResponse)
async def admin_list_electric_stations(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[ElectricStationStatusEnum] = Query(None),
    connector_type: Optional[str] = Query(None),
    min_power_kw: Optional[float] = Query(None, gt=0),
    max_power_kw: Optional[float] = Query(None, gt=0),
    min_price_per_kwh: Optional[float] = Query(None, gt=0),
    max_price_per_kwh: Optional[float] = Query(None, gt=0),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    is_24_7: Optional[bool] = Query(None),
    has_promotions: Optional[bool] = Query(None),
    has_parking: Optional[bool] = Query(None),
    has_waiting_room: Optional[bool] = Query(None),
    has_cafe: Optional[bool] = Query(None),
    has_restroom: Optional[bool] = Query(None),
    accepts_cards: Optional[bool] = Query(None),
    has_mobile_app: Optional[bool] = Query(None),
    requires_membership: Optional[bool] = Query(None),
    has_available_points: Optional[bool] = Query(None),
    operator: Optional[str] = Query(None),
    network: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None)
):
    """Получение списка всех электрозаправок (включая ожидающие модерации)"""
    filters = ElectricStationFilter(
        connector_type=connector_type,
        min_power_kw=min_power_kw,
        max_power_kw=max_power_kw,
        min_price_per_kwh=min_price_per_kwh,
        max_price_per_kwh=max_price_per_kwh,
        min_rating=min_rating,
        is_24_7=is_24_7,
        has_promotions=has_promotions,
        has_parking=has_parking,
        has_waiting_room=has_waiting_room,
        has_cafe=has_cafe,
        has_restroom=has_restroom,
        accepts_cards=accepts_cards,
        has_mobile_app=has_mobile_app,
        requires_membership=requires_membership,
        has_available_points=has_available_points,
        operator=operator,
        network=network,
        search_query=search_query,
        status=status
    )
    
    stations, total = get_electric_stations(db, skip=skip, limit=limit, filters=filters)
    
    station_responses = []
    for station in stations:
        station_dict = ElectricStationResponse.model_validate(station).model_dump()
        main_photo = next((p for p in station.photos if p.is_main), None)
        if main_photo:
            station_dict["main_photo"] = main_photo.photo_url
        station_responses.append(ElectricStationResponse(**station_dict))
    
    return ElectricStationListResponse(
        electric_stations=station_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{station_id}", response_model=ElectricStationDetailResponse)
async def admin_get_electric_station(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение детальной информации об электрозаправке"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    # Получаем отзывы
    from app.services.electric_station_service.crud import get_reviews_by_station
    reviews, _ = get_reviews_by_station(db, station_id, skip=0, limit=50)
    
    # Преобразуем отзывы с именами пользователей
    from app.services.user_service.crud import get_user_extended_by_id
    review_responses = []
    for review in reviews:
        from app.schemas.electric_station import ElectricStationReviewResponse
        review_dict = ElectricStationReviewResponse.model_validate(review).model_dump()
        user_extended = get_user_extended_by_id(db, review.user_id)
        if user_extended:
            review_dict["user_name"] = user_extended.name
        review_responses.append(ElectricStationReviewResponse(**review_dict))
    
    station_dict = ElectricStationDetailResponse.model_validate(station).model_dump()
    station_dict["reviews"] = review_responses
    
    # Находим главную фотографию
    main_photo = next((p for p in station.photos if p.is_main), None)
    if main_photo:
        station_dict["main_photo"] = main_photo.photo_url
    
    return ElectricStationDetailResponse(**station_dict)


@router.put("/{station_id}", response_model=ElectricStationResponse)
async def admin_update_electric_station(
    station_id: int,
    station_update: ElectricStationAdminUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление электрозаправки"""
    station = update_electric_station(db, station_id, station_update)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    db.refresh(station)
    return ElectricStationResponse.model_validate(station)


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_electric_station(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление электрозаправки"""
    success = delete_electric_station(db, station_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    return None


@router.post("/{station_id}/approve", response_model=ElectricStationResponse)
async def admin_approve_electric_station(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Одобрение электрозаправки"""
    station = approve_electric_station(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    return ElectricStationResponse.model_validate(station)


@router.post("/{station_id}/reject", response_model=ElectricStationResponse)
async def admin_reject_electric_station(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Отклонение электрозаправки"""
    station = reject_electric_station(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    return ElectricStationResponse.model_validate(station)


@router.post("/{station_id}/photos", response_model=ElectricStationPhotoResponse, status_code=status.HTTP_201_CREATED)
async def admin_upload_electric_station_photo(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    is_main: bool = Query(False),
    order: int = Query(0, ge=0)
):
    """Загрузка фотографии для электрозаправки (админ)"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла. Разрешены: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    photo_url = save_uploaded_photo(file, station_id)
    
    photo = add_electric_station_photo(
        db=db,
        station_id=station_id,
        photo_url=photo_url,
        is_main=is_main,
        order=order,
        uploaded_by_admin_id=current_user.id
    )
    
    return ElectricStationPhotoResponse.model_validate(photo)


@router.delete("/{station_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_electric_station_photo(
    station_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление фотографии электрозаправки (админ)"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    photo = next((p for p in station.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена"
        )
    
    delete_electric_station_photo(db, photo_id)
    return None


@router.post("/{station_id}/photos/{photo_id}/set-main", response_model=ElectricStationPhotoResponse)
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
    
    return ElectricStationPhotoResponse.model_validate(photo)


@router.post("/{station_id}/charging-points", response_model=List[ChargingPointResponse])
async def admin_update_charging_points(
    station_id: int,
    points: BulkChargingPointUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление зарядных точек электрозаправки (админ)"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    updated_points = bulk_update_charging_points(
        db=db,
        station_id=station_id,
        points=points.charging_points
    )
    
    return [ChargingPointResponse.model_validate(p) for p in updated_points]










