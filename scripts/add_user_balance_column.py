"""
Добавляет колонку balance в таблицу users (для доставки).
Запуск: python scripts/add_user_balance_column.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.database import engine


def main():
    with engine.connect() as conn:
        # PostgreSQL: добавить колонку, если её ещё нет
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS balance DOUBLE PRECISION NOT NULL DEFAULT 0
        """))
        conn.commit()
    print("OK: users.balance column added or already exists.")


if __name__ == "__main__":
    main()
