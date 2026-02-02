"""
CRUD операции для водителей
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
import math

from app.models.driver import (
    Driver,
    DriverDocument,
    Vehicle,
    Region,
    DriverStatus,
    DocumentType,
    DocumentStatus,
)
from app.schemas.driver import (
    DriverCreate,
    DriverUpdate,
    DriverDocumentCreate,
    DriverDocumentUpdate,
    VehicleCreate,
    VehicleUpdate,
)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Вычисляет расстояние между двумя точками в км (формула Haversine)"""
    R = 6371  # Радиус Земли в км
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
        math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


# ==================== Driver CRUD ====================

def create_driver(db: Session, driver_data: DriverCreate, user_id: int) -> Driver:
    """Создание нового водителя"""
    driver = Driver(
        user_id=user_id,
        phone_number=driver_data.phone_number,
        full_name=driver_data.full_name,
        email=driver_data.email,
        region_id=driver_data.region_id,
        status=DriverStatus.PENDING,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def create_driver_by_admin(db: Session, driver_data) -> Driver:
    """Создание водителя администратором"""
    # Проверяем, не существует ли уже водитель с таким user_id
    existing_driver = get_driver_by_user_id(db, driver_data.user_id)
    if existing_driver:
        raise ValueError(f"Водитель с user_id={driver_data.user_id} уже существует")
    
    # Проверяем, не существует ли уже водитель с таким номером телефона
    existing_phone = get_driver_by_phone(db, driver_data.phone_number)
    if existing_phone:
        raise ValueError(f"Водитель с номером {driver_data.phone_number} уже существует")
    
    driver = Driver(
        user_id=driver_data.user_id,
        phone_number=driver_data.phone_number,
        full_name=driver_data.full_name,
        email=driver_data.email,
        region_id=driver_data.region_id,
        status=driver_data.status if hasattr(driver_data, 'status') and driver_data.status else DriverStatus.PENDING,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def create_driver_by_admin(db: Session, driver_data) -> Driver:
    """Создание водителя администратором"""
    # Проверяем, не существует ли уже водитель с таким user_id
    existing_driver = get_driver_by_user_id(db, driver_data.user_id)
    if existing_driver:
        raise ValueError(f"Водитель с user_id={driver_data.user_id} уже существует")
    
    # Проверяем, не существует ли уже водитель с таким номером телефона
    existing_phone = get_driver_by_phone(db, driver_data.phone_number)
    if existing_phone:
        raise ValueError(f"Водитель с номером {driver_data.phone_number} уже существует")
    
    driver = Driver(
        user_id=driver_data.user_id,
        phone_number=driver_data.phone_number,
        full_name=driver_data.full_name,
        email=driver_data.email,
        region_id=driver_data.region_id,
        status=driver_data.status if hasattr(driver_data, 'status') and driver_data.status else DriverStatus.PENDING,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def get_driver_by_id(db: Session, driver_id: int) -> Optional[Driver]:
    """Получение водителя по ID"""
    return db.query(Driver).filter(Driver.id == driver_id).first()


def get_driver_by_user_id(db: Session, user_id: int) -> Optional[Driver]:
    """Получение водителя по user_id"""
    return db.query(Driver).filter(Driver.user_id == user_id).first()


def get_driver_by_phone(db: Session, phone_number: str) -> Optional[Driver]:
    """Получение водителя по номеру телефона"""
    return db.query(Driver).filter(Driver.phone_number == phone_number).first()


def get_drivers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[DriverStatus] = None,
    region_id: Optional[int] = None,
    is_online: Optional[bool] = None,
    search: Optional[str] = None,
) -> List[Driver]:
    """Получение списка водителей с фильтрацией и поиском"""
    query = db.query(Driver)
    
    if status:
        query = query.filter(Driver.status == status)
    if region_id:
        query = query.filter(Driver.region_id == region_id)
    if is_online is not None:
        query = query.filter(Driver.is_online == is_online)
    
    # Поиск по имени или номеру телефона
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Driver.full_name.ilike(search_pattern)) |
            (Driver.phone_number.ilike(search_pattern))
        )
    
    return query.order_by(Driver.created_at.desc()).offset(skip).limit(limit).all()


def assign_user_as_driver(
    db: Session,
    user_id: int,
    full_name: Optional[str] = None,
    region_id: Optional[int] = None,
    status: DriverStatus = DriverStatus.PENDING
) -> Driver:
    """Назначение пользователя водителем (админ)"""
    from app.crud.user import get_user_by_id
    
    # Проверяем, существует ли пользователь
    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"Пользователь с ID {user_id} не найден")
    
    # Проверяем, не является ли уже водителем
    existing_driver = get_driver_by_user_id(db, user_id)
    if existing_driver:
        raise ValueError(f"Пользователь с ID {user_id} уже является водителем")
    
    # Используем имя пользователя или переданное имя
    driver_full_name = full_name or user.fullname or user.phone_number
    
    # Создаем водителя
    driver = Driver(
        user_id=user_id,
        phone_number=user.phone_number,
        full_name=driver_full_name,
        email=None,
        region_id=region_id,
        status=status,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def update_driver(db: Session, driver_id: int, driver_data: DriverUpdate) -> Optional[Driver]:
    """Обновление данных водителя"""
    driver = get_driver_by_id(db, driver_id)
    if not driver:
        return None
    
    update_data = driver_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(driver, field, value)
    
    driver.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(driver)
    return driver


def update_driver_status(
    db: Session,
    driver_id: int,
    status: DriverStatus,
    admin_comment: Optional[str] = None
) -> Optional[Driver]:
    """Обновление статуса водителя"""
    driver = get_driver_by_id(db, driver_id)
    if not driver:
        return None
    
    driver.status = status
    driver.admin_comment = admin_comment
    
    if status == DriverStatus.APPROVED and not driver.approved_at:
        driver.approved_at = datetime.utcnow()
    
    if status == DriverStatus.ONLINE or status == DriverStatus.OFFLINE:
        driver.is_online = (status == DriverStatus.ONLINE)
    
    driver.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(driver)
    return driver


def update_driver_online_status(
    db: Session,
    driver_id: int,
    is_online: bool
) -> Optional[Driver]:
    """Обновление статуса онлайн/оффлайн водителя"""
    driver = get_driver_by_id(db, driver_id)
    if not driver:
        return None
    
    # Только одобренные водители (APPROVED, ONLINE, OFFLINE) могут менять статус онлайн
    if driver.status not in (DriverStatus.APPROVED, DriverStatus.ONLINE, DriverStatus.OFFLINE):
        return None  # PENDING, REJECTED, SUSPENDED — нельзя менять is_online
    
    driver.is_online = is_online
    if is_online:
        driver.status = DriverStatus.ONLINE
    else:
        driver.status = DriverStatus.OFFLINE
    
    driver.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(driver)
    return driver


def get_nearby_drivers(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    region_id: Optional[int] = None,
    limit: int = 20
) -> List[Driver]:
    """Поиск водителей поблизости"""
    # Базовый запрос: только одобренные и онлайн водители
    query = db.query(Driver).filter(
        and_(
            Driver.status == DriverStatus.ONLINE,
            Driver.is_online == True,
            Driver.current_latitude.isnot(None),
            Driver.current_longitude.isnot(None),
        )
    )
    
    if region_id:
        query = query.filter(Driver.region_id == region_id)
    
    drivers = query.all()
    
    # Фильтруем по расстоянию
    nearby_drivers = []
    for driver in drivers:
        distance = haversine_distance(
            latitude, longitude,
            driver.current_latitude, driver.current_longitude
        )
        if distance <= radius_km:
            nearby_drivers.append((driver, distance))
    
    # Сортируем по расстоянию
    nearby_drivers.sort(key=lambda x: x[1])
    
    # Возвращаем только водителей (без расстояния)
    return [driver for driver, _ in nearby_drivers[:limit]]


def get_driver_statistics(db: Session, driver_id: int) -> Optional[dict]:
    """Получение статистики водителя"""
    driver = get_driver_by_id(db, driver_id)
    if not driver:
        return None
    
    # Статистика за сегодня
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    orders_today = 0
    earnings_today = 0.0
    
    # Время онлайн сегодня (упрощенный расчет)
    online_hours_today = None  # Можно реализовать более сложную логику
    
    return {
        "total_orders": driver.total_orders,
        "completed_orders": driver.completed_orders,
        "cancelled_orders": driver.cancelled_orders,
        "rating": driver.rating,
        "total_earnings": driver.total_earnings,
        "balance": driver.balance,
        "online_hours_today": online_hours_today,
        "orders_today": orders_today,
        "earnings_today": float(earnings_today),
    }


# ==================== Driver Document CRUD ====================

def create_driver_document(
    db: Session,
    driver_id: int,
    document_data: DriverDocumentCreate
) -> DriverDocument:
    """Создание документа водителя"""
    document = DriverDocument(
        driver_id=driver_id,
        document_type=document_data.document_type,
        front_image_url=document_data.front_image_url,
        back_image_url=document_data.back_image_url,
        document_number=document_data.document_number,
        issue_date=document_data.issue_date,
        expiry_date=document_data.expiry_date,
        status=DocumentStatus.PENDING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_driver_document(
    db: Session,
    driver_id: int,
    document_type: DocumentType
) -> Optional[DriverDocument]:
    """Получение документа водителя по типу"""
    return db.query(DriverDocument).filter(
        and_(
            DriverDocument.driver_id == driver_id,
            DriverDocument.document_type == document_type
        )
    ).first()


def get_driver_documents(db: Session, driver_id: int) -> List[DriverDocument]:
    """Получение всех документов водителя"""
    return db.query(DriverDocument).filter(
        DriverDocument.driver_id == driver_id
    ).all()


def update_driver_document(
    db: Session,
    driver_id: int,
    document_type: DocumentType,
    document_data: DriverDocumentUpdate
) -> Optional[DriverDocument]:
    """Обновление документа водителя"""
    document = get_driver_document(db, driver_id, document_type)
    if not document:
        return None
    
    update_data = document_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    # При обновлении документа статус сбрасывается на pending
    document.status = DocumentStatus.PENDING
    document.uploaded_at = datetime.utcnow()
    
    db.commit()
    db.refresh(document)
    return document


def update_document_status(
    db: Session,
    document_id: int,
    status: DocumentStatus,
    admin_comment: Optional[str] = None
) -> Optional[DriverDocument]:
    """Обновление статуса документа (админ)"""
    document = db.query(DriverDocument).filter(
        DriverDocument.id == document_id
    ).first()
    if not document:
        return None
    
    document.status = status
    document.admin_comment = admin_comment
    document.verified_at = datetime.utcnow() if status == DocumentStatus.APPROVED else None
    
    db.commit()
    db.refresh(document)
    return document


# ==================== Vehicle CRUD ====================

def create_vehicle(db: Session, driver_id: int, vehicle_data: VehicleCreate) -> Vehicle:
    """Создание транспортного средства"""
    vehicle = Vehicle(
        driver_id=driver_id,
        vehicle_type=vehicle_data.vehicle_type,
        brand=vehicle_data.brand,
        model=vehicle_data.model,
        year=vehicle_data.year,
        color=vehicle_data.color,
        license_plate=vehicle_data.license_plate,
        vehicle_passport_number=vehicle_data.vehicle_passport_number,
        photo_url=vehicle_data.photo_url,
        capacity_kg=vehicle_data.capacity_kg,
        volume_m3=vehicle_data.volume_m3,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def get_vehicle_by_driver_id(db: Session, driver_id: int) -> Optional[Vehicle]:
    """Получение ТС по driver_id"""
    return db.query(Vehicle).filter(Vehicle.driver_id == driver_id).first()


def update_vehicle(
    db: Session,
    driver_id: int,
    vehicle_data: VehicleUpdate
) -> Optional[Vehicle]:
    """Обновление ТС"""
    vehicle = get_vehicle_by_driver_id(db, driver_id)
    if not vehicle:
        return None
    
    update_data = vehicle_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)
    
    vehicle.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vehicle)
    return vehicle

