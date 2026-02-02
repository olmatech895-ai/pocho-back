"""
API эндпоинты для электрозаправок (пользовательские)
"""
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.electric_station_service.crud import (
    create_electric_station,
    get_electric_station_by_id,
    get_electric_stations,
    create_review,
    get_reviews_by_station,
    update_review,
    delete_review,
    add_electric_station_photo,
    get_electric_station_photos,
    delete_electric_station_photo,
    bulk_update_charging_points,
    get_charging_points_by_station,
    delete_charging_point,
)
from app.schemas.electric_station import (
    ElectricStationCreate,
    ElectricStationResponse,
    ElectricStationDetailResponse,
    ElectricStationListResponse,
    ElectricStationFilter,
    ChargingPointCreate,
    ChargingPointResponse,
    ElectricStationReviewCreate,
    ElectricStationReviewResponse,
    ElectricStationReviewUpdate,
    ElectricStationPhotoResponse,
    BulkChargingPointUpdate,
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
async def create_electric_station_endpoint(
    station_data: ElectricStationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание новой электрозаправки (требует модерации)"""
    station = create_electric_station(
        db=db,
        station_data=station_data,
        created_by_user_id=current_user.id
    )
    
    db.refresh(station)
    return ElectricStationResponse.model_validate(station)


@router.get("/", response_model=ElectricStationListResponse)
async def list_electric_stations(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    connector_type: Optional[str] = Query(None, description="Тип разъема"),
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
    search_query: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None, ge=-90, le=90),
    longitude: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: Optional[float] = Query(None, gt=0)
):
    """Получение списка электрозаправок с фильтрацией"""
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
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )
    
    stations, total = get_electric_stations(db, skip=skip, limit=limit, filters=filters)
    
    # Преобразуем в ответы
    station_responses = []
    for station in stations:
        station_dict = ElectricStationResponse.model_validate(station).model_dump()
        # Находим главную фотографию
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


@router.get("/favorites", response_model=ElectricStationListResponse)
async def get_favorite_electric_stations(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """Получение списка избранных электрозаправок пользователя"""
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.favorites_service.crud import get_favorites_by_user_id

    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )

    favorites_list = get_favorites_by_user_id(db, user_extended.id, favorite_type="charging_station")
    station_responses = []
    for fav in favorites_list:
        station = get_electric_station_by_id(db, fav.place_id)
        if station and station.status == ElectricStationStatus.APPROVED:
            station_dict = ElectricStationResponse.model_validate(station).model_dump()
            main_photo = next((p for p in station.photos if p.is_main), None)
            if main_photo:
                station_dict["main_photo"] = main_photo.photo_url
            station_responses.append(ElectricStationResponse(**station_dict))

    total = len(station_responses)
    paginated = station_responses[skip : skip + limit]

    return ElectricStationListResponse(
        electric_stations=paginated,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/{station_id}/favorite", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_electric_station_to_favorites(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Добавить электрозаправку в избранное"""
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.favorites_service.crud import create_favorite
    from app.schemas.user_extended import UserFavoriteCreate

    station = get_electric_station_by_id(db, station_id)
    if not station or station.status != ElectricStationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )

    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )

    favorite_data = UserFavoriteCreate(favorite_type="charging_station", place_id=station_id)
    created_favorite = create_favorite(db, user_extended.id, favorite_data)
    return {"message": "Добавлено в избранное", "id": created_favorite.id}


@router.delete("/{station_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_electric_station_from_favorites(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удалить электрозаправку из избранного"""
    from app.services.user_service.crud import get_user_extended_by_id
    from app.services.favorites_service.crud import delete_favorite

    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )

    deleted = delete_favorite(db, user_extended.id, "charging_station", station_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не была в избранном"
        )


@router.get("/{station_id}", response_model=ElectricStationDetailResponse)
async def get_electric_station(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение детальной информации об электрозаправке"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    if station.status != ElectricStationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    # Получаем отзывы
    reviews, _ = get_reviews_by_station(db, station_id, skip=0, limit=50)
    
    # Преобразуем отзывы с именами пользователей
    from app.services.user_service.crud import get_user_extended_by_id
    review_responses = []
    for review in reviews:
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


@router.post("/{station_id}/photos", response_model=ElectricStationPhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_electric_station_photo(
    station_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
    is_main: bool = Query(False),
    order: int = Query(0, ge=0)
):
    """Загрузка фотографии для электрозаправки"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    # Проверяем права: только создатель или админ может добавлять фото
    if station.created_by_user_id != current_user.id and not current_user.is_admin:
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
    photo_url = save_uploaded_photo(file, station_id)
    
    # Добавляем в БД
    photo = add_electric_station_photo(
        db=db,
        station_id=station_id,
        photo_url=photo_url,
        is_main=is_main,
        order=order,
        uploaded_by_user_id=current_user.id if not current_user.is_admin else None,
        uploaded_by_admin_id=current_user.id if current_user.is_admin else None
    )
    
    return ElectricStationPhotoResponse.model_validate(photo)


@router.delete("/{station_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_electric_station_photo_endpoint(
    station_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление фотографии электрозаправки"""
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
    
    # Проверяем права
    if station.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления фотографий"
        )
    
    delete_electric_station_photo(db, photo_id)
    return None


@router.post("/{station_id}/charging-points", response_model=List[ChargingPointResponse])
async def update_charging_points(
    station_id: int,
    points: BulkChargingPointUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление зарядных точек электрозаправки"""
    station = get_electric_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    # Проверяем права: только создатель или админ может обновлять точки
    if station.created_by_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для обновления зарядных точек"
        )
    
    updated_points = bulk_update_charging_points(
        db=db,
        station_id=station_id,
        points=points.charging_points
    )
    
    return [ChargingPointResponse.model_validate(p) for p in updated_points]


@router.post("/{station_id}/reviews", response_model=ElectricStationReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_electric_station_review(
    station_id: int,
    review_data: ElectricStationReviewCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание отзыва об электрозаправке"""
    station = get_electric_station_by_id(db, station_id)
    if not station or station.status != ElectricStationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Электрозаправка не найдена"
        )
    
    review = create_review(
        db=db,
        station_id=station_id,
        user_id=current_user.id,
        review_data=review_data
    )
    
    # Получаем имя пользователя
    from app.services.user_service.crud import get_user_extended_by_id
    user_extended = get_user_extended_by_id(db, current_user.id)
    review_dict = ElectricStationReviewResponse.model_validate(review).model_dump()
    if user_extended:
        review_dict["user_name"] = user_extended.name
    
    return ElectricStationReviewResponse(**review_dict)


@router.put("/{station_id}/reviews/{review_id}", response_model=ElectricStationReviewResponse)
async def update_electric_station_review(
    station_id: int,
    review_id: int,
    review_update: ElectricStationReviewUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление отзыва об электрозаправке"""
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
    review_dict = ElectricStationReviewResponse.model_validate(review).model_dump()
    if user_extended:
        review_dict["user_name"] = user_extended.name
    
    return ElectricStationReviewResponse(**review_dict)


@router.delete("/{station_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_electric_station_review(
    station_id: int,
    review_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление отзыва об электрозаправке"""
    success = delete_review(db, review_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )
    return None










