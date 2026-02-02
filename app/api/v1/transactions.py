"""
API эндпоинты для транзакций
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.transactions_service.crud import (
    get_transactions_by_user_id,
    create_transaction,
    get_transactions_count,
)
from app.services.user_service.crud import get_user_extended_by_id, update_user_balance
from app.schemas.user_extended import (
    TransactionCreate,
    TransactionResponse,
)

router = APIRouter()


@router.get("", response_model=list[TransactionResponse])
async def get_transactions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Получение транзакций пользователя"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    transactions = get_transactions_by_user_id(db, user_extended.id, limit, offset)
    return [TransactionResponse.model_validate(t) for t in transactions]


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_user_transaction(
    transaction: TransactionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Создание транзакции"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    # Создаем транзакцию
    created_transaction = create_transaction(db, user_extended.id, transaction)
    
    # Обновляем баланс пользователя
    update_user_balance(db, user_extended.id, transaction.amount)
    
    return TransactionResponse.model_validate(created_transaction)


@router.get("/count", response_model=dict)
async def get_transactions_count(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение количества транзакций"""
    user_extended = get_user_extended_by_id(db, current_user.id)
    if not user_extended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль не найден"
        )
    
    count = get_transactions_count(db, user_extended.id)
    return {"count": count}

