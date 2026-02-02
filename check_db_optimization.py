"""
Скрипт для проверки оптимизации базы данных
Проверяет наличие индексов и настройки подключений
"""
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text, inspect
from app.database import engine, SessionLocal
from app.models import (
    GasStation, Restaurant, ServiceStation, CarWash, ElectricStation,
    User, UserExtended, Transaction, Advertisement
)

def check_indexes():
    """Проверка наличия индексов в базе данных"""
    print("=" * 60)
    print("ПРОВЕРКА ИНДЕКСОВ В БАЗЕ ДАННЫХ")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Получаем список всех таблиц
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        for table_name in tables:
            indexes = inspector.get_indexes(table_name)
            print(f"\nТаблица: {table_name}")
            print(f"  Индексов: {len(indexes)}")
            
            if indexes:
                for idx in indexes:
                    columns = ", ".join(idx['column_names'])
                    unique = "UNIQUE" if idx.get('unique') else ""
                    print(f"    - {idx['name']} {unique}: ({columns})")
            else:
                print("    ⚠️  Нет индексов!")
        
        # Проверка конкретных важных индексов
        print("\n" + "=" * 60)
        print("ПРОВЕРКА КРИТИЧЕСКИХ ИНДЕКСОВ")
        print("=" * 60)
        
        critical_indexes = {
            "gas_stations": ["latitude", "longitude", "status", "created_at"],
            "restaurants": ["latitude", "longitude", "status", "created_at"],
            "service_stations": ["latitude", "longitude", "status", "created_at"],
            "car_washes": ["latitude", "longitude", "status", "created_at"],
            "electric_stations": ["latitude", "longitude", "status", "created_at"],
            "users": ["phone_number", "is_active", "is_admin"],
            "users_extended": ["user_id", "phone", "email"],
            "transactions": ["user_id", "created_at", "type"],
            "advertisements": ["status", "position", "start_date", "end_date"],
        }
        
        for table_name, columns in critical_indexes.items():
            if table_name in tables:
                indexes = inspector.get_indexes(table_name)
                indexed_columns = set()
                for idx in indexes:
                    indexed_columns.update(idx['column_names'])
                
                missing = [col for col in columns if col not in indexed_columns]
                if missing:
                    print(f"\n⚠️  {table_name}: отсутствуют индексы на {', '.join(missing)}")
                else:
                    print(f"✅ {table_name}: все критичные индексы присутствуют")
        
    finally:
        db.close()


def check_connection_pool():
    """Проверка настроек пула соединений"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ПУЛА СОЕДИНЕНИЙ")
    print("=" * 60)
    
    pool = engine.pool
    print(f"Размер пула: {pool.size()}")
    print(f"Максимальный размер: {pool._max_overflow + pool.size()}")
    print(f"Текущие соединения: {pool.checkedout()}")
    print(f"Свободные соединения: {pool.checkedin()}")
    
    # Рекомендации
    print("\nРекомендации:")
    if pool.size() < 10:
        print("⚠️  Размер пула соединений мал. Рекомендуется: 10-20")
    if pool._max_overflow < 20:
        print("⚠️  Максимальный overflow мал. Рекомендуется: 20-50")


def check_postgresql_settings():
    """Проверка настроек PostgreSQL"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА НАСТРОЕК POSTGRESQL")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Проверка max_connections
        result = db.execute(text("SHOW max_connections"))
        max_conn = result.scalar()
        print(f"max_connections: {max_conn}")
        
        # Проверка shared_buffers
        result = db.execute(text("SHOW shared_buffers"))
        shared_buffers = result.scalar()
        print(f"shared_buffers: {shared_buffers}")
        
        # Проверка work_mem
        result = db.execute(text("SHOW work_mem"))
        work_mem = result.scalar()
        print(f"work_mem: {work_mem}")
        
        # Проверка effective_cache_size
        result = db.execute(text("SHOW effective_cache_size"))
        effective_cache = result.scalar()
        print(f"effective_cache_size: {effective_cache}")
        
        # Рекомендации
        print("\nРекомендации для нагрузки 20000 пользователей:")
        print("- max_connections: минимум 200")
        print("- shared_buffers: минимум 256MB (лучше 512MB-1GB)")
        print("- work_mem: 16MB-32MB")
        print("- effective_cache_size: 1GB-2GB")
        
    except Exception as e:
        print(f"⚠️  Ошибка при проверке настроек PostgreSQL: {e}")
    finally:
        db.close()


def check_table_sizes():
    """Проверка размеров таблиц"""
    print("\n" + "=" * 60)
    print("РАЗМЕРЫ ТАБЛИЦ")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        query = text("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 20
        """)
        
        result = db.execute(query)
        rows = result.fetchall()
        
        for row in rows:
            print(f"{row.tablename}: {row.size}")
        
    except Exception as e:
        print(f"⚠️  Ошибка при проверке размеров: {e}")
    finally:
        db.close()


def check_slow_queries():
    """Проверка медленных запросов (если включен pg_stat_statements)"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА МЕДЛЕННЫХ ЗАПРОСОВ")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Проверяем, включен ли pg_stat_statements
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
            )
        """))
        
        if result.scalar():
            query = text("""
                SELECT 
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    max_exec_time
                FROM pg_stat_statements
                WHERE mean_exec_time > 100
                ORDER BY mean_exec_time DESC
                LIMIT 10
            """)
            
            result = db.execute(query)
            rows = result.fetchall()
            
            if rows:
                print("Медленные запросы (>100ms):")
                for row in rows:
                    print(f"\n  Среднее время: {row.mean_exec_time:.2f}ms")
                    print(f"  Вызовов: {row.calls}")
                    print(f"  Запрос: {row.query[:200]}...")
            else:
                print("✅ Медленных запросов не найдено")
        else:
            print("ℹ️  pg_stat_statements не включен. Для детального анализа:")
            print("   CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
        
    except Exception as e:
        print(f"⚠️  Ошибка при проверке медленных запросов: {e}")
    finally:
        db.close()


def main():
    """Главная функция"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ОПТИМИЗАЦИИ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    check_indexes()
    check_connection_pool()
    check_postgresql_settings()
    check_table_sizes()
    check_slow_queries()
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 60)
    print("\nРекомендации:")
    print("1. Убедитесь, что все критичные индексы созданы")
    print("2. Настройте пул соединений для высокой нагрузки")
    print("3. Оптимизируйте настройки PostgreSQL")
    print("4. Используйте кэширование для часто запрашиваемых данных")
    print("5. Рассмотрите использование Redis для сессий и кэша")


if __name__ == "__main__":
    main()






