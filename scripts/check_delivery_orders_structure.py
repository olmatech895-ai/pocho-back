"""
Проверка структуры таблицы delivery_orders.
Запуск: python scripts/check_delivery_orders_structure.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.database import engine


def main():
    with engine.connect() as conn:
        # Получаем список всех колонок в таблице
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'delivery_orders'
            ORDER BY ordinal_position;
        """))
        
        print("Columns in delivery_orders table:")
        print("-" * 80)
        for row in result:
            col_name, data_type, is_nullable, col_default = row
            nullable_str = "NULL" if is_nullable == "YES" else "NOT NULL"
            default_str = f" DEFAULT {col_default}" if col_default else ""
            print(f"{col_name:30} {data_type:20} {nullable_str:10} {default_str}")
        
        # Проверяем наличие customer_id
        result_customer = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_name = 'delivery_orders' AND column_name = 'customer_id';
        """))
        
        if result_customer.fetchone():
            print("\nWARNING: Found 'customer_id' column. This might be causing issues.")
            print("Checking if it's used...")
            
            # Проверяем, есть ли данные в customer_id
            result_data = conn.execute(text("""
                SELECT COUNT(*) as total, 
                       COUNT(customer_id) as with_customer_id
                FROM delivery_orders;
            """))
            
            total, with_customer_id = result_data.fetchone()
            print(f"Total orders: {total}, Orders with customer_id: {with_customer_id}")


if __name__ == "__main__":
    main()
