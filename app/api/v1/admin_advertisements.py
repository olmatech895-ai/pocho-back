"""
API эндпоинты для рекламы (администраторские)
"""
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_admin_user
from app.services.advertisement_service.crud import (
    create_advertisement,
    get_advertisement_by_id,
    get_advertisements,
    update_advertisement,
    delete_advertisement,
    get_advertisement_views,
    get_advertisement_clicks,
    get_advertisement_statistics,
)
from app.schemas.advertisement import (
    AdvertisementCreate,
    AdvertisementUpdate,
    AdvertisementResponse,
    AdvertisementDetailResponse,
    AdvertisementListResponse,
    AdvertisementFilter,
    AdvertisementViewResponse,
    AdvertisementClickResponse,
    AdvertisementStatisticsResponse,
    AdvertisementTypeEnum,
    AdvertisementStatusEnum,
    AdvertisementPositionEnum,
)
from app.models.advertisement import AdvertisementClick
from app.core.config import settings

router = APIRouter()

# Директория для загрузки изображений рекламы
ADVERTISEMENT_IMAGES_DIR = Path(settings.UPLOAD_DIR) / "advertisements"
ADVERTISEMENT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_image(file: UploadFile) -> str:
    """Сохранение загруженного изображения и возврат URL"""
    file_extension = Path(file.filename).suffix if file.filename else ".jpg"
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = ADVERTISEMENT_IMAGES_DIR / unique_filename
    
    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
    
    # Возвращаем URL
    relative_path = f"uploads/advertisements/{unique_filename}"
    return f"{settings.BASE_URL}/{relative_path}"


@router.post("/", response_model=AdvertisementResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_advertisement(
    advertisement_data: AdvertisementCreate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание новой рекламы"""
    advertisement = create_advertisement(
        db=db,
        advertisement_data=advertisement_data,
        created_by_admin_id=current_user.id
    )
    
    return AdvertisementResponse.model_validate(advertisement)


@router.post("/upload-image", status_code=status.HTTP_201_CREATED)
async def admin_upload_advertisement_image(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    file: Annotated[UploadFile, File(...)]
):
    """Загрузка изображения для рекламы"""
    # Проверяем тип файла
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла. Разрешены: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    # Сохраняем файл
    image_url = save_uploaded_image(file)
    
    return {"image_url": image_url}


@router.get("/", response_model=AdvertisementListResponse)
async def admin_list_advertisements(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    ad_type: Optional[AdvertisementTypeEnum] = Query(None),
    position: Optional[AdvertisementPositionEnum] = Query(None),
    status: Optional[AdvertisementStatusEnum] = Query(None),
    is_active: Optional[bool] = Query(None),
    target_audience: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None)
):
    """Получение списка всех реклам"""
    filters = AdvertisementFilter(
        ad_type=ad_type,
        position=position,
        status=status,
        is_active=is_active,
        target_audience=target_audience,
        search_query=search_query
    )
    
    advertisements, total = get_advertisements(db, skip=skip, limit=limit, filters=filters)
    
    return AdvertisementListResponse(
        advertisements=[AdvertisementResponse.model_validate(ad) for ad in advertisements],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{advertisement_id}", response_model=AdvertisementDetailResponse)
async def admin_get_advertisement(
    advertisement_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение детальной информации о рекламе"""
    advertisement = get_advertisement_by_id(db, advertisement_id)
    if not advertisement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Реклама не найдена"
        )
    
    # Получаем последние просмотры и клики
    views, _ = get_advertisement_views(db, advertisement_id, skip=0, limit=10)
    clicks, _ = get_advertisement_clicks(db, advertisement_id, skip=0, limit=10)
    
    advertisement_dict = AdvertisementDetailResponse.model_validate(advertisement).model_dump()
    advertisement_dict["recent_views"] = [AdvertisementViewResponse.model_validate(v) for v in views]
    advertisement_dict["recent_clicks"] = [AdvertisementClickResponse.model_validate(c) for c in clicks]
    
    return AdvertisementDetailResponse(**advertisement_dict)


@router.put("/{advertisement_id}", response_model=AdvertisementResponse)
async def admin_update_advertisement(
    advertisement_id: int,
    advertisement_update: AdvertisementUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление рекламы"""
    advertisement = update_advertisement(db, advertisement_id, advertisement_update)
    if not advertisement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Реклама не найдена"
        )
    
    return AdvertisementResponse.model_validate(advertisement)


@router.delete("/{advertisement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_advertisement(
    advertisement_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Удаление рекламы"""
    success = delete_advertisement(db, advertisement_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Реклама не найдена"
        )
    return None


@router.get("/{advertisement_id}/statistics", response_model=AdvertisementStatisticsResponse)
async def admin_get_advertisement_statistics(
    advertisement_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение статистики по рекламе"""
    statistics = get_advertisement_statistics(db, advertisement_id)
    if not statistics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Реклама не найдена"
        )
    
    return AdvertisementStatisticsResponse(**statistics)


@router.get("/{advertisement_id}/views", response_model=List[AdvertisementViewResponse])
async def admin_get_advertisement_views(
    advertisement_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Получение просмотров рекламы"""
    views, _ = get_advertisement_views(db, advertisement_id, skip=skip, limit=limit)
    return [AdvertisementViewResponse.model_validate(v) for v in views]


@router.get("/{advertisement_id}/clicks", response_model=List[AdvertisementClickResponse])
async def admin_get_advertisement_clicks(
    advertisement_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Получение кликов по рекламе"""
    clicks, _ = get_advertisement_clicks(db, advertisement_id, skip=skip, limit=limit)
    return [AdvertisementClickResponse.model_validate(c) for c in clicks]

