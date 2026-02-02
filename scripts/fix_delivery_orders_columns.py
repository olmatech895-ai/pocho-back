"""
Исправление структуры таблицы delivery_orders: удаление/изменение старых колонок.
Запуск: python scripts/fix_delivery_orders_columns.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.database import engine


def main():
    with engine.connect() as conn:
        try:
            print("Fixing delivery_orders table structure...")
            
            # 1. Делаем customer_id nullable (если используется) или удаляем
            try:
                # Сначала проверяем, используется ли customer_id
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM delivery_orders WHERE customer_id IS NOT NULL;
                """))
                count = result.scalar()
                
                if count > 0:
                    print(f"Found {count} orders with customer_id. Making it nullable...")
                    # Если есть данные, делаем nullable
                    conn.execute(text("""
                        ALTER TABLE delivery_orders 
                        ALTER COLUMN customer_id DROP NOT NULL;
                    """))
                    print("OK: customer_id is now nullable")
                else:
                    print("No data in customer_id. Dropping column...")
                    conn.execute(text("""
                        ALTER TABLE delivery_orders 
                        DROP COLUMN IF EXISTS customer_id;
                    """))
                    print("OK: customer_id column dropped")
            except Exception as e:
                print(f"Warning: Could not modify customer_id: {e}")
            
            # 2. Делаем старые колонки nullable, если они есть
            old_columns = [
                'region_id',
                'pickup_contact_name',
                'pickup_contact_phone',
                'delivery_address',  # Старая колонка, теперь используется dropoff_address
                'delivery_latitude',  # Старая колонка, теперь используется dropoff_latitude
                'delivery_longitude',  # Старая колонка, теперь используется dropoff_longitude
                'delivery_contact_name',
                'delivery_contact_phone',
                'cargo_description',
                'cargo_weight_kg',
                'cargo_volume_m3',
                'base_price',
                'distance_km',
                'distance_price',
                'total_price',
                'payment_method',
                'accepted_at',
                'picked_up_at',
                'delivered_at',
                'cancelled_at',
                'customer_comment',
                'driver_comment',
                'rating',
                'review',
            ]
            
            for col in old_columns:
                try:
                    # Проверяем существование колонки
                    result = conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns
                        WHERE table_name = 'delivery_orders' AND column_name = :col_name;
                    """), {"col_name": col})
                    
                    if result.fetchone():
                        # Делаем nullable
                        conn.execute(text(f"""
                            ALTER TABLE delivery_orders 
                            ALTER COLUMN {col} DROP NOT NULL;
                        """))
                        print(f"OK: {col} is now nullable")
                except Exception as e:
                    # Если колонка не существует или уже nullable, пропускаем
                    pass
            
            # 3. Убеждаемся, что новые колонки имеют правильные типы
            new_columns_config = {
                'user_id': 'INTEGER NOT NULL',
                'dropoff_latitude': 'DOUBLE PRECISION',
                'dropoff_longitude': 'DOUBLE PRECISION',
                'dropoff_address': 'VARCHAR(500)',
                'parcel_description': 'TEXT',
                'parcel_estimated_value': 'DOUBLE PRECISION',
                'delivery_cost': 'DOUBLE PRECISION',
                'canceled_at': 'TIMESTAMP WITH TIME ZONE',
                'cancel_reason': 'TEXT',
                'canceled_by_user_id': 'INTEGER',
                'updated_at': 'TIMESTAMP WITH TIME ZONE',
                'status': 'VARCHAR(50) NOT NULL DEFAULT \'created\'',
            }
            
            for col, col_def in new_columns_config.items():
                try:
                    # Проверяем существование колонки
                    result = conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns
                        WHERE table_name = 'delivery_orders' AND column_name = :col_name;
                    """), {"col_name": col})
                    
                    if not result.fetchone():
                        # Добавляем колонку, если её нет
                        if 'NOT NULL' in col_def:
                            # Для NOT NULL колонок нужно значение по умолчанию
                            if col == 'user_id':
                                # user_id обязателен, но если есть customer_id, можно использовать его
                                conn.execute(text("""
                                    ALTER TABLE delivery_orders 
                                    ADD COLUMN user_id INTEGER;
                                """))
                                # Заполняем user_id из customer_id, если возможно
                                conn.execute(text("""
                                    UPDATE delivery_orders 
                                    SET user_id = customer_id 
                                    WHERE user_id IS NULL AND customer_id IS NOT NULL;
                                """))
                                # Теперь делаем NOT NULL
                                conn.execute(text("""
                                    ALTER TABLE delivery_orders 
                                    ALTER COLUMN user_id SET NOT NULL;
                                """))
                            else:
                                conn.execute(text(f"""
                                    ALTER TABLE delivery_orders 
                                    ADD COLUMN {col} {col_def};
                                """))
                        else:
                            conn.execute(text(f"""
                                ALTER TABLE delivery_orders 
                                ADD COLUMN {col} {col_def};
                            """))
                        print(f"OK: Added column {col}")
                except Exception as e:
                    print(f"Warning: Could not add/modify {col}: {e}")
            
            conn.commit()
            print("\nOK: Migration completed successfully!")
            
        except Exception as e:
            conn.rollback()
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
