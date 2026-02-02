"""
API endpoints для водителей (клиентская часть)
"""
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.driver import (
    DriverCreate,
    DriverResponse,
    DriverUpdate,
    DriverOnlineStatus,
    DriverDocumentCreate,
    DriverDocumentResponse,
    DriverDocumentUpdate,
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
    DriverStatistics,
)
from app.services.driver_service.crud import (
    create_driver,
    get_driver_by_user_id,
    get_driver_by_id,
    update_driver,
    update_driver_online_status,
    get_driver_statistics,
    create_driver_document,
    get_driver_documents,
    get_driver_document,
    update_driver_document,
    create_vehicle,
    get_vehicle_by_driver_id,
    update_vehicle,
)
from app.models.driver import DocumentType
from app.core.config import settings
import os
from pathlib import Path

router = APIRouter(prefix="/drivers", tags=["Водители"])


@router.post("/register", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
async def register_as_driver(
    driver_data: DriverCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Регистрация пользователя как водителя"""
    # Проверяем, не зарегистрирован ли уже как водитель
    existing_driver = get_driver_by_user_id(db, current_user.id)
    if existing_driver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже зарегистрированы как водитель"
        )
    
    # Проверяем уникальность номера телефона
    from app.services.driver_service.crud import get_driver_by_phone
    if get_driver_by_phone(db, driver_data.phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Водитель с таким номером телефона уже зарегистрирован"
        )
    
    driver = create_driver(db, driver_data, current_user.id)
    return driver


@router.get("/me", response_model=DriverResponse)
async def get_my_driver_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение профиля текущего водителя"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    return driver


@router.put("/me", response_model=DriverResponse)
async def update_my_driver_profile(
    driver_data: DriverUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление профиля водителя"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    updated_driver = update_driver(db, driver.id, driver_data)
    return updated_driver


@router.post("/me/online-status", response_model=DriverResponse)
@router.patch("/me/status", response_model=DriverResponse)
async def update_online_status(
    online_status: DriverOnlineStatus,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Изменение статуса водителя (онлайн/оффлайн).
    Доступно водителям со статусом approved/online/offline.
    POST /me/online-status или PATCH /me/status, body: {"is_online": true/false}
    """
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    updated_driver = update_driver_online_status(db, driver.id, online_status.is_online)
    if not updated_driver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно изменить статус. Водитель должен быть одобрен (статус pending/rejected/suspended не могут выходить в сеть)"
        )
    return updated_driver


@router.get("/me/statistics", response_model=DriverStatistics)
async def get_my_statistics(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение статистики водителя"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    stats = get_driver_statistics(db, driver.id)
    return stats


# ==================== Documents ====================

@router.post("/me/documents", response_model=DriverDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_data: DriverDocumentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Загрузка документа водителя"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    # Проверяем, не существует ли уже документ такого типа
    existing_doc = get_driver_document(db, driver.id, document_data.document_type)
    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Документ типа {document_data.document_type.value} уже загружен"
        )
    
    document = create_driver_document(db, driver.id, document_data)
    return document


@router.get("/me/documents", response_model=List[DriverDocumentResponse])
async def get_my_documents(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение всех документов водителя"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    documents = get_driver_documents(db, driver.id)
    return documents


@router.get("/me/documents/{document_type}", response_model=DriverDocumentResponse)
async def get_my_document(
    document_type: DocumentType,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение конкретного документа водителя"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    document = get_driver_document(db, driver.id, document_type)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Документ типа {document_type.value} не найден"
        )
    return document


@router.put("/me/documents/{document_type}", response_model=DriverDocumentResponse)
async def update_my_document(
    document_type: DocumentType,
    document_data: DriverDocumentUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление документа водителя"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    updated_document = update_driver_document(db, driver.id, document_type, document_data)
    if not updated_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Документ типа {document_type.value} не найден"
        )
    return updated_document


# ==================== Vehicle ====================

@router.post("/me/vehicle", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def register_vehicle(
    vehicle_data: VehicleCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Регистрация транспортного средства"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    # Проверяем, не зарегистрировано ли уже ТС
    existing_vehicle = get_vehicle_by_driver_id(db, driver.id)
    if existing_vehicle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Транспортное средство уже зарегистрировано"
        )
    
    vehicle = create_vehicle(db, driver.id, vehicle_data)
    return vehicle


@router.get("/me/vehicle", response_model=VehicleResponse)
async def get_my_vehicle(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение транспортного средства водителя"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    vehicle = get_vehicle_by_driver_id(db, driver.id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транспортное средство не зарегистрировано"
        )
    return vehicle


@router.put("/me/vehicle", response_model=VehicleResponse)
async def update_my_vehicle(
    vehicle_data: VehicleUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Обновление транспортного средства"""
    driver = get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не зарегистрированы как водитель"
        )
    
    updated_vehicle = update_vehicle(db, driver.id, vehicle_data)
    if not updated_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транспортное средство не зарегистрировано"
        )
    return updated_vehicle

