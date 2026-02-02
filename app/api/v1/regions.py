"""
API endpoints для регионов Узбекистана
"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.driver import RegionResponse
from app.models.driver import Region

router = APIRouter(prefix="/regions", tags=["Регионы"])


@router.get("", response_model=List[RegionResponse])
async def get_regions(
    is_active: bool = Query(None, description="Фильтр по активности региона"),
    db: Annotated[Session, Depends(get_db)] = None
):
    """Получение списка регионов Узбекистана"""
    query = db.query(Region)
    
    if is_active is not None:
        query = query.filter(Region.is_active == is_active)
    
    regions = query.order_by(Region.display_order, Region.name_ru).all()
    return regions


@router.get("/{region_id}", response_model=RegionResponse)
async def get_region(
    region_id: int,
    db: Annotated[Session, Depends(get_db)] = None
):
    """Получение региона по ID"""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Регион не найден"
        )
    return region

