"""
API endpoints для администраторов (управление водителями)
"""
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.schemas.driver import (
    DriverResponse,
    DriverStatusUpdate,
    DriverDocumentResponse,
    DriverDocumentStatusUpdate,
    DriverCreateByAdmin,
    AssignDriverRequest,
)
from app.services.driver_service.crud import (
    create_driver_by_admin,
    assign_user_as_driver,
    get_drivers,
    get_driver_by_id,
    get_driver_by_user_id,
    get_driver_by_phone,
    update_driver_status,
    get_driver_documents,
    update_document_status,
)
from app.models.driver import DriverStatus, DocumentStatus, DocumentType

router = APIRouter(prefix="/admin/drivers", tags=["Админ: Водители"])


@router.post("", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
async def create_driver_admin(
    driver_data: DriverCreateByAdmin,
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """
    Создание водителя администратором (полная форма)
    
    Требует указания всех данных: user_id, phone_number, full_name и т.д.
    Для простого назначения пользователя водителем используйте /assign
    """
    try:
        driver = create_driver_by_admin(db, driver_data)
        return driver
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/assign", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
async def assign_driver(
    request: AssignDriverRequest,
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """
    Назначение пользователя водителем (админ)
    
    Упрощенный способ назначения существующего пользователя водителем.
    Автоматически использует данные пользователя (номер телефона, имя).
    
    - **user_id**: ID пользователя для назначения водителем (обязательно)
    - **full_name**: Полное имя водителя (опционально, если не указано - используется имя пользователя)
    - **region_id**: ID региона (опционально)
    - **status**: Начальный статус водителя (по умолчанию PENDING)
    
    ⚠️ Пользователь должен существовать в системе.
    ⚠️ Пользователь не должен быть уже водителем.
    """
    try:
        driver = assign_user_as_driver(
            db=db,
            user_id=request.user_id,
            full_name=request.full_name,
            region_id=request.region_id,
            status=request.status
        )
        return driver
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при назначении водителя: {str(e)}"
        )


@router.get("", response_model=List[DriverResponse])
async def get_all_drivers(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=100, description="Максимальное количество записей"),
    status: Optional[DriverStatus] = Query(None, description="Фильтр по статусу водителя"),
    region_id: Optional[int] = Query(None, description="Фильтр по региону"),
    is_online: Optional[bool] = Query(None, description="Фильтр по статусу онлайн"),
    search: Optional[str] = Query(None, description="Поиск по имени или номеру телефона"),
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """
    Получение списка всех водителей (админ)
    
    Поддерживает фильтрацию по статусу, региону, онлайн статусу и поиск по имени/телефону.
    """
    drivers = get_drivers(
        db,
        skip=skip,
        limit=limit,
        status=status,
        region_id=region_id,
        is_online=is_online,
        search=search
    )
    return drivers


@router.get("/{driver_id}", response_model=DriverResponse)
async def get_driver(
    driver_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """Получение водителя по ID (админ)"""
    driver = get_driver_by_id(db, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Водитель не найден"
        )
    return driver


@router.put("/{driver_id}/status", response_model=DriverResponse)
async def update_driver_status_admin(
    driver_id: int,
    status_data: DriverStatusUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """Обновление статуса водителя (админ)"""
    driver = get_driver_by_id(db, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Водитель не найден"
        )
    
    updated_driver = update_driver_status(
        db,
        driver_id,
        status_data.status,
        status_data.admin_comment
    )
    return updated_driver


@router.get("/{driver_id}/documents", response_model=List[DriverDocumentResponse])
async def get_driver_documents_admin(
    driver_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """Получение всех документов водителя (админ)"""
    driver = get_driver_by_id(db, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Водитель не найден"
        )
    
    documents = get_driver_documents(db, driver_id)
    return documents


@router.put("/{driver_id}/documents/{document_id}/status", response_model=DriverDocumentResponse)
async def update_document_status_admin(
    driver_id: int,
    document_id: int,
    status_data: DriverDocumentStatusUpdate,
    current_user: Annotated[User, Depends(get_current_admin_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """Обновление статуса документа водителя (админ)"""
    driver = get_driver_by_id(db, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Водитель не найден"
        )
    
    updated_document = update_document_status(
        db,
        document_id,
        status_data.status,
        status_data.admin_comment
    )
    
    if not updated_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден"
        )
    
    # Проверяем, все ли документы одобрены, чтобы автоматически одобрить водителя
    if status_data.status == DocumentStatus.APPROVED:
        all_documents = get_driver_documents(db, driver_id)
        required_documents = [DocumentType.PASSPORT, DocumentType.DRIVING_LICENSE, DocumentType.VEHICLE_PASSPORT]
        approved_documents = [doc.document_type for doc in all_documents if doc.status == DocumentStatus.APPROVED]
        
        # Если все обязательные документы одобрены и водитель еще не одобрен
        if all(doc_type in approved_documents for doc_type in required_documents) and driver.status == DriverStatus.PENDING:
            update_driver_status(db, driver_id, DriverStatus.APPROVED, "Все документы проверены и одобрены")
    
    return updated_document



