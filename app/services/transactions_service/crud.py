"""
CRUD операции для Transactions Service
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.user_extended import Transaction
from app.schemas.user_extended import TransactionCreate


def get_transactions_by_user_id(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[Transaction]:
    """Получение транзакций пользователя"""
    return db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.created_at.desc()).limit(limit).offset(offset).all()


def get_transaction_by_id(
    db: Session,
    transaction_id: int
) -> Optional[Transaction]:
    """Получение транзакции по ID"""
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def create_transaction(
    db: Session,
    user_id: int,
    transaction: TransactionCreate
) -> Transaction:
    """Создание транзакции"""
    db_transaction = Transaction(
        user_id=user_id,
        type=transaction.type,
        amount=transaction.amount,
        description=transaction.description,
        extra_data=transaction.extra_data
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def get_transactions_count(db: Session, user_id: int) -> int:
    """Получение количества транзакций пользователя"""
    return db.query(Transaction).filter(Transaction.user_id == user_id).count()

