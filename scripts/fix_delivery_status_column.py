"""
Исправление типа колонки status в delivery_orders: преобразование из enum в VARCHAR.
Запуск: python scripts/fix_delivery_status_column.py
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
            # Проверяем тип колонки status
            result = conn.execute(text("""
                SELECT data_type, udt_name 
                FROM information_schema.columns 
                WHERE table_name = 'delivery_orders' AND column_name = 'status';
            """))
            
            row = result.fetchone()
            if row:
                data_type, udt_name = row
                print(f"Current column type status: {data_type} ({udt_name})")
                
                # Если это enum (USER-DEFINED), преобразуем в VARCHAR
                if data_type == 'USER-DEFINED':
                    print("Found enum type. Converting to VARCHAR...")
                    
                    # 1. Создаём временную колонку VARCHAR
                    conn.execute(text("""
                        ALTER TABLE delivery_orders 
                        ADD COLUMN status_temp VARCHAR(50);
                    """))
                    
                    # 2. Копируем данные с преобразованием
                    conn.execute(text("""
                        UPDATE delivery_orders 
                        SET status_temp = status::text;
                    """))
                    
                    # 3. Удаляем старую колонку
                    conn.execute(text("""
                        ALTER TABLE delivery_orders 
                        DROP COLUMN status;
                    """))
                    
                    # 4. Переименовываем временную колонку
                    conn.execute(text("""
                        ALTER TABLE delivery_orders 
                        RENAME COLUMN status_temp TO status;
                    """))
                    
                    # 5. Устанавливаем NOT NULL и DEFAULT
                    conn.execute(text("""
                        ALTER TABLE delivery_orders 
                        ALTER COLUMN status SET NOT NULL,
                        ALTER COLUMN status SET DEFAULT 'created';
                    """))
                    
                    print("OK: Column status converted to VARCHAR")
                elif data_type == 'character varying' or data_type == 'varchar':
                    print("OK: Column status already has VARCHAR type. No changes needed.")
                else:
                    print(f"WARNING: Unexpected column type: {data_type}. Manual check required.")
            
            # Проверяем тип колонок в delivery_order_status_history
            result_history = conn.execute(text("""
                SELECT column_name, data_type, udt_name 
                FROM information_schema.columns 
                WHERE table_name = 'delivery_order_status_history' 
                AND column_name IN ('from_status', 'to_status');
            """))
            
            history_rows = result_history.fetchall()
            for col_name, data_type, udt_name in history_rows:
                if data_type == 'USER-DEFINED':
                    print(f"Found enum type in {col_name}. Converting to VARCHAR...")
                    
                    # Аналогичное преобразование для истории статусов
                    conn.execute(text(f"""
                        ALTER TABLE delivery_order_status_history 
                        ADD COLUMN {col_name}_temp VARCHAR(50);
                    """))
                    
                    conn.execute(text(f"""
                        UPDATE delivery_order_status_history 
                        SET {col_name}_temp = {col_name}::text;
                    """))
                    
                    conn.execute(text(f"""
                        ALTER TABLE delivery_order_status_history 
                        DROP COLUMN {col_name};
                    """))
                    
                    conn.execute(text(f"""
                        ALTER TABLE delivery_order_status_history 
                        RENAME COLUMN {col_name}_temp TO {col_name};
                    """))
                    
                    if col_name == 'to_status':
                        conn.execute(text("""
                            ALTER TABLE delivery_order_status_history 
                            ALTER COLUMN to_status SET NOT NULL;
                        """))
                    
                    print(f"OK: Column {col_name} converted to VARCHAR")
            
            conn.commit()
            print("\nOK: Migration completed successfully!")
            
        except Exception as e:
            conn.rollback()
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
