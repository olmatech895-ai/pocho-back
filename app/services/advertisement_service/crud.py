"""
CRUD операции для Advertisement Service
"""
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func as sql_func, distinct

from app.models.advertisement import (
    Advertisement,
    AdvertisementView,
    AdvertisementClick,
    AdvertisementType,
    AdvertisementStatus,
    AdvertisementPosition,
)
from app.schemas.advertisement import (
    AdvertisementCreate,
    AdvertisementUpdate,
    AdvertisementFilter,
    AdvertisementViewCreate,
    AdvertisementClickCreate,
)


# ==================== Advertisement CRUD ====================

def create_advertisement(
    db: Session,
    advertisement_data: AdvertisementCreate,
    created_by_admin_id: int
) -> Advertisement:
    """Создание рекламы"""
    advertisement_dict = advertisement_data.model_dump()
    advertisement_dict["created_by_admin_id"] = created_by_admin_id
    
    db_advertisement = Advertisement(**advertisement_dict)
    db.add(db_advertisement)
    db.commit()
    db.refresh(db_advertisement)
    return db_advertisement


def get_advertisement_by_id(db: Session, advertisement_id: int) -> Optional[Advertisement]:
    """Получение рекламы по ID"""
    return db.query(Advertisement).filter(Advertisement.id == advertisement_id).first()


def get_advertisements(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[AdvertisementFilter] = None
) -> Tuple[List[Advertisement], int]:
    """Получение списка рекламы с фильтрацией"""
    query = db.query(Advertisement)
    
    # Фильтр по типу
    if filters and filters.ad_type:
        query = query.filter(Advertisement.ad_type == filters.ad_type.value)
    
    # Фильтр по позиции
    if filters and filters.position:
        query = query.filter(Advertisement.position == filters.position.value)
    
    # Фильтр по статусу
    if filters and filters.status:
        query = query.filter(Advertisement.status == filters.status.value)
    
    # Фильтр по активности
    if filters and filters.is_active is not None:
        query = query.filter(Advertisement.is_active == filters.is_active)
    
    # Фильтр по целевой аудитории
    if filters and filters.target_audience:
        query = query.filter(Advertisement.target_audience == filters.target_audience)
    
    # Поиск по названию или описанию
    if filters and filters.search_query:
        search_term = f"%{filters.search_query}%"
        query = query.filter(
            or_(
                Advertisement.title.ilike(search_term),
                Advertisement.description.ilike(search_term)
            )
        )
    
    # Подсчет общего количества
    total = query.count()
    
    # Применяем пагинацию и сортировку
    advertisements = query.order_by(
        Advertisement.priority.desc(),
        Advertisement.display_order.asc(),
        Advertisement.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return advertisements, total


def get_active_advertisements_for_position(
    db: Session,
    position: AdvertisementPosition,
    user_id: Optional[int] = None,
    target_audience: Optional[str] = None
) -> List[Advertisement]:
    """Получение активных реклам для определенной позиции"""
    now = datetime.utcnow()
    
    query = db.query(Advertisement).filter(
        and_(
            Advertisement.status == AdvertisementStatus.ACTIVE,
            Advertisement.is_active == True,
            Advertisement.position == position.value,
            or_(
                Advertisement.start_date.is_(None),
                Advertisement.start_date <= now
            ),
            or_(
                Advertisement.end_date.is_(None),
                Advertisement.end_date >= now
            )
        )
    )
    
    # Фильтр по целевой аудитории
    if target_audience:
        query = query.filter(
            or_(
                Advertisement.target_audience.is_(None),
                Advertisement.target_audience == target_audience,
                Advertisement.target_audience == "all"
            )
        )
    
    # Сортируем по приоритету и порядку
    advertisements = query.order_by(
        Advertisement.priority.desc(),
        Advertisement.display_order.asc()
    ).all()
    
    return advertisements


def update_advertisement(
    db: Session,
    advertisement_id: int,
    advertisement_update: AdvertisementUpdate
) -> Optional[Advertisement]:
    """Обновление рекламы"""
    advertisement = get_advertisement_by_id(db, advertisement_id)
    if not advertisement:
        return None
    
    update_data = advertisement_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(advertisement, field, value)
    
    db.commit()
    db.refresh(advertisement)
    return advertisement


def delete_advertisement(db: Session, advertisement_id: int) -> bool:
    """Удаление рекламы"""
    advertisement = get_advertisement_by_id(db, advertisement_id)
    if not advertisement:
        return False
    
    db.delete(advertisement)
    db.commit()
    return True


def increment_views_count(db: Session, advertisement_id: int):
    """Увеличение счетчика просмотров"""
    advertisement = get_advertisement_by_id(db, advertisement_id)
    if advertisement:
        advertisement.views_count += 1
        db.commit()


def increment_clicks_count(db: Session, advertisement_id: int):
    """Увеличение счетчика кликов"""
    advertisement = get_advertisement_by_id(db, advertisement_id)
    if advertisement:
        advertisement.clicks_count += 1
        db.commit()


# ==================== Advertisement View CRUD ====================

def create_advertisement_view(
    db: Session,
    advertisement_id: int,
    view_data: AdvertisementViewCreate,
    user_id: Optional[int] = None
) -> AdvertisementView:
    """Создание записи о просмотре рекламы"""
    view = AdvertisementView(
        advertisement_id=advertisement_id,
        user_id=user_id,
        ip_address=view_data.ip_address,
        user_agent=view_data.user_agent,
        device_type=view_data.device_type,
        app_version=view_data.app_version
    )
    db.add(view)
    
    # Увеличиваем счетчик просмотров
    increment_views_count(db, advertisement_id)
    
    db.commit()
    db.refresh(view)
    return view


def get_advertisement_views(
    db: Session,
    advertisement_id: int,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[AdvertisementView], int]:
    """Получение просмотров рекламы"""
    query = db.query(AdvertisementView).filter(
        AdvertisementView.advertisement_id == advertisement_id
    )
    total = query.count()
    views = query.order_by(AdvertisementView.viewed_at.desc()).offset(skip).limit(limit).all()
    return views, total


def get_unique_views_count(db: Session, advertisement_id: int) -> int:
    """Получение количества уникальных просмотров (по пользователям)"""
    return db.query(distinct(AdvertisementView.user_id)).filter(
        and_(
            AdvertisementView.advertisement_id == advertisement_id,
            AdvertisementView.user_id.isnot(None)
        )
    ).count()


def get_views_count_by_period(
    db: Session,
    advertisement_id: int,
    start_date: datetime,
    end_date: datetime
) -> int:
    """Получение количества просмотров за период"""
    return db.query(AdvertisementView).filter(
        and_(
            AdvertisementView.advertisement_id == advertisement_id,
            AdvertisementView.viewed_at >= start_date,
            AdvertisementView.viewed_at <= end_date
        )
    ).count()


# ==================== Advertisement Click CRUD ====================

def create_advertisement_click(
    db: Session,
    advertisement_id: int,
    click_data: AdvertisementClickCreate,
    user_id: Optional[int] = None
) -> AdvertisementClick:
    """Создание записи о клике по рекламе"""
    click = AdvertisementClick(
        advertisement_id=advertisement_id,
        user_id=user_id,
        ip_address=click_data.ip_address,
        user_agent=click_data.user_agent,
        device_type=click_data.device_type
    )
    db.add(click)
    
    # Увеличиваем счетчик кликов
    increment_clicks_count(db, advertisement_id)
    
    db.commit()
    db.refresh(click)
    return click


def get_advertisement_clicks(
    db: Session,
    advertisement_id: int,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[AdvertisementClick], int]:
    """Получение кликов по рекламе"""
    query = db.query(AdvertisementClick).filter(
        AdvertisementClick.advertisement_id == advertisement_id
    )
    total = query.count()
    clicks = query.order_by(AdvertisementClick.clicked_at.desc()).offset(skip).limit(limit).all()
    return clicks, total


def get_unique_clicks_count(db: Session, advertisement_id: int) -> int:
    """Получение количества уникальных кликов (по пользователям)"""
    return db.query(distinct(AdvertisementClick.user_id)).filter(
        and_(
            AdvertisementClick.advertisement_id == advertisement_id,
            AdvertisementClick.user_id.isnot(None)
        )
    ).count()


def get_clicks_count_by_period(
    db: Session,
    advertisement_id: int,
    start_date: datetime,
    end_date: datetime
) -> int:
    """Получение количества кликов за период"""
    return db.query(AdvertisementClick).filter(
        and_(
            AdvertisementClick.advertisement_id == advertisement_id,
            AdvertisementClick.clicked_at >= start_date,
            AdvertisementClick.clicked_at <= end_date
        )
    ).count()


# ==================== Statistics ====================

def get_advertisement_statistics(
    db: Session,
    advertisement_id: int
) -> dict:
    """Получение статистики по рекламе"""
    advertisement = get_advertisement_by_id(db, advertisement_id)
    if not advertisement:
        return None
    
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = datetime(now.year, now.month, 1)
    
    views_today = get_views_count_by_period(db, advertisement_id, today_start, now)
    clicks_today = get_clicks_count_by_period(db, advertisement_id, today_start, now)
    
    views_this_week = get_views_count_by_period(db, advertisement_id, week_start, now)
    clicks_this_week = get_clicks_count_by_period(db, advertisement_id, week_start, now)
    
    views_this_month = get_views_count_by_period(db, advertisement_id, month_start, now)
    clicks_this_month = get_clicks_count_by_period(db, advertisement_id, month_start, now)
    
    unique_views = get_unique_views_count(db, advertisement_id)
    unique_clicks = get_unique_clicks_count(db, advertisement_id)
    
    # CTR (Click-Through Rate) в процентах
    ctr = 0.0
    if advertisement.views_count > 0:
        ctr = (advertisement.clicks_count / advertisement.views_count) * 100
    
    return {
        "advertisement_id": advertisement_id,
        "title": advertisement.title,
        "views_count": advertisement.views_count,
        "clicks_count": advertisement.clicks_count,
        "click_through_rate": round(ctr, 2),
        "unique_views": unique_views,
        "unique_clicks": unique_clicks,
        "views_today": views_today,
        "clicks_today": clicks_today,
        "views_this_week": views_this_week,
        "clicks_this_week": clicks_this_week,
        "views_this_month": views_this_month,
        "clicks_this_month": clicks_this_month,
    }










