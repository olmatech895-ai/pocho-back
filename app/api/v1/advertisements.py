"""
API эндпоинты для рекламы (клиентские)
"""
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user_optional
from app.services.advertisement_service.crud import (
    get_active_advertisements_for_position,
    create_advertisement_view,
    create_advertisement_click,
)
from app.schemas.advertisement import (
    AdvertisementForClientResponse,
    AdvertisementViewCreate,
    AdvertisementClickCreate,
    AdvertisementPositionEnum,
)
from app.models.advertisement import AdvertisementPosition

router = APIRouter()


@router.get("/", response_model=List[AdvertisementForClientResponse])
async def get_advertisements(
    position: AdvertisementPositionEnum = Query(..., description="Позиция рекламы в приложении"),
    current_user: Annotated[Optional[User], Depends(get_current_user_optional)] = None,
    db: Annotated[Session, Depends(get_db)] = None
):
    """
    Получение активных рекламных блоков для определенной позиции
    
    Этот эндпоинт используется клиентским приложением для получения рекламы,
    которую нужно показать пользователю на определенной странице.
    """
    from app.services.advertisement_service.crud import get_active_advertisements_for_position
    
    # Определяем целевую аудиторию (можно расширить логику)
    target_audience = None
    if current_user:
        # Здесь можно добавить логику определения целевой аудитории
        # Например, если у пользователя есть премиум подписка
        target_audience = "all"
    
    advertisements = get_active_advertisements_for_position(
        db=db,
        position=position,
        user_id=current_user.id if current_user else None,
        target_audience=target_audience
    )
    
    return [AdvertisementForClientResponse.model_validate(ad) for ad in advertisements]


@router.post("/{advertisement_id}/view", status_code=status.HTTP_201_CREATED)
async def register_advertisement_view(
    advertisement_id: int,
    request: Request,
    current_user: Annotated[Optional[User], Depends(get_current_user_optional)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
    ip_address: Optional[str] = Query(None, description="IP адрес (если не указан, берется из запроса)"),
    user_agent: Optional[str] = Query(None, description="User-Agent (если не указан, берется из заголовков)"),
    device_type: Optional[str] = Query(None, description="Тип устройства (mobile, tablet, desktop)"),
    app_version: Optional[str] = Query(None, description="Версия приложения")
):
    """
    Регистрация просмотра рекламы
    
    Этот эндпоинт вызывается клиентским приложением каждый раз,
    когда реклама показывается пользователю.
    """
    from app.services.advertisement_service.crud import get_advertisement_by_id
    
    # Проверяем существование рекламы
    advertisement = get_advertisement_by_id(db, advertisement_id)
    if not advertisement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Реклама не найдена"
        )
    
    # Получаем IP адрес из запроса, если не указан
    if not ip_address:
        ip_address = request.client.host if request.client else None
    
    # Получаем User-Agent из заголовков, если не указан
    if not user_agent:
        user_agent = request.headers.get("user-agent")
    
    # Создаем запись о просмотре
    view_data = AdvertisementViewCreate(
        ip_address=ip_address,
        user_agent=user_agent,
        device_type=device_type,
        app_version=app_version
    )
    
    create_advertisement_view(
        db=db,
        advertisement_id=advertisement_id,
        view_data=view_data,
        user_id=current_user.id if current_user else None
    )
    
    return {"message": "Просмотр зарегистрирован", "advertisement_id": advertisement_id}


@router.post("/{advertisement_id}/click", status_code=status.HTTP_201_CREATED)
async def register_advertisement_click(
    advertisement_id: int,
    request: Request,
    current_user: Annotated[Optional[User], Depends(get_current_user_optional)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
    ip_address: Optional[str] = Query(None, description="IP адрес (если не указан, берется из запроса)"),
    user_agent: Optional[str] = Query(None, description="User-Agent (если не указан, берется из заголовков)"),
    device_type: Optional[str] = Query(None, description="Тип устройства (mobile, tablet, desktop)")
):
    """
    Регистрация клика по рекламе
    
    Этот эндпоинт вызывается клиентским приложением когда пользователь
    кликает на рекламу.
    """
    from app.services.advertisement_service.crud import get_advertisement_by_id
    
    # Проверяем существование рекламы
    advertisement = get_advertisement_by_id(db, advertisement_id)
    if not advertisement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Реклама не найдена"
        )
    
    # Получаем IP адрес из запроса, если не указан
    if not ip_address:
        ip_address = request.client.host if request.client else None
    
    # Получаем User-Agent из заголовков, если не указан
    if not user_agent:
        user_agent = request.headers.get("user-agent")
    
    # Создаем запись о клике
    click_data = AdvertisementClickCreate(
        ip_address=ip_address,
        user_agent=user_agent,
        device_type=device_type
    )
    
    create_advertisement_click(
        db=db,
        advertisement_id=advertisement_id,
        click_data=click_data,
        user_id=current_user.id if current_user else None
    )
    
    return {"message": "Клик зарегистрирован", "advertisement_id": advertisement_id}

