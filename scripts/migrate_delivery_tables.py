"""
Создаёт таблицы доставки и добавляет недостающие колонки в delivery_orders.
Запуск: python scripts/migrate_delivery_tables.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.database import engine


def run(conn, sql):
    conn.execute(text(sql))


def main():
    with engine.connect() as conn:
        # 1. Таблица delivery_tariffs (создаём первой, т.к. delivery_orders ссылается на неё)
        run(conn, """
            CREATE TABLE IF NOT EXISTS delivery_tariffs (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200),
                cost_per_km DOUBLE PRECISION NOT NULL,
                min_total DOUBLE PRECISION NOT NULL,
                base_fixed DOUBLE PRECISION NOT NULL DEFAULT 0,
                extra_coefficients TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """)

        # 2. Таблица delivery_orders — добавляем колонки, если таблица уже есть
        run(conn, """
            CREATE TABLE IF NOT EXISTS delivery_orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                driver_id INTEGER REFERENCES drivers(id),
                tariff_id INTEGER REFERENCES delivery_tariffs(id),
                pickup_latitude DOUBLE PRECISION NOT NULL,
                pickup_longitude DOUBLE PRECISION NOT NULL,
                pickup_address VARCHAR(500),
                dropoff_latitude DOUBLE PRECISION NOT NULL,
                dropoff_longitude DOUBLE PRECISION NOT NULL,
                dropoff_address VARCHAR(500),
                parcel_description TEXT,
                parcel_estimated_value DOUBLE PRECISION,
                delivery_cost DOUBLE PRECISION NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'created',
                canceled_at TIMESTAMP WITH TIME ZONE,
                cancel_reason TEXT,
                canceled_by_user_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """)

        # Если таблица delivery_orders уже существовала без этих колонок — добавляем по одной
        cols = [
            "user_id INTEGER REFERENCES users(id)",
            "driver_id INTEGER REFERENCES drivers(id)",
            "tariff_id INTEGER REFERENCES delivery_tariffs(id)",
            "pickup_latitude DOUBLE PRECISION",
            "pickup_longitude DOUBLE PRECISION",
            "pickup_address VARCHAR(500)",
            "dropoff_latitude DOUBLE PRECISION",
            "dropoff_longitude DOUBLE PRECISION",
            "dropoff_address VARCHAR(500)",
            "parcel_description TEXT",
            "parcel_estimated_value DOUBLE PRECISION",
            "delivery_cost DOUBLE PRECISION",
            "status VARCHAR(50) DEFAULT 'created'",
            "canceled_at TIMESTAMP WITH TIME ZONE",
            "cancel_reason TEXT",
            "canceled_by_user_id INTEGER REFERENCES users(id)",
            "created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()",
            "updated_at TIMESTAMP WITH TIME ZONE",
        ]
        for col_def in cols:
            try:
                run(conn, f"ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS {col_def}")
            except Exception:
                pass

        # 3. Таблица delivery_order_status_history
        run(conn, """
            CREATE TABLE IF NOT EXISTS delivery_order_status_history (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES delivery_orders(id),
                from_status VARCHAR(50),
                to_status VARCHAR(50) NOT NULL,
                source VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        # 4. Таблица user_balance_logs
        run(conn, """
            CREATE TABLE IF NOT EXISTS user_balance_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                order_id INTEGER REFERENCES delivery_orders(id),
                amount DOUBLE PRECISION NOT NULL,
                type VARCHAR(50) NOT NULL,
                description TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        conn.commit()
    print("OK: delivery tables migrated.")


if __name__ == "__main__":
    main()
