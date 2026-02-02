"""
Скрипт для добавления регионов Узбекистана в базу данных
"""
import sys
import io
from pathlib import Path

# Исправление кодировки для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.driver import Region


REGIONS_DATA = [
    {
        "name_uz": "Toshkent",
        "name_ru": "Ташкент",
        "name_en": "Tashkent",
        "center_latitude": 41.2995,
        "center_longitude": 69.2401,
        "display_order": 1,
        "is_active": True,
    },
    {
        "name_uz": "Toshkent viloyati",
        "name_ru": "Ташкентская область",
        "name_en": "Tashkent Region",
        "center_latitude": 41.2044,
        "center_longitude": 69.2167,
        "display_order": 2,
        "is_active": True,
    },
    {
        "name_uz": "Andijon",
        "name_ru": "Андижан",
        "name_en": "Andijan",
        "center_latitude": 40.7834,
        "center_longitude": 72.3441,
        "display_order": 3,
        "is_active": True,
    },
    {
        "name_uz": "Buxoro",
        "name_ru": "Бухара",
        "name_en": "Bukhara",
        "center_latitude": 39.7681,
        "center_longitude": 64.4556,
        "display_order": 4,
        "is_active": True,
    },
    {
        "name_uz": "Farg'ona",
        "name_ru": "Фергана",
        "name_en": "Fergana",
        "center_latitude": 40.3864,
        "center_longitude": 71.7864,
        "display_order": 5,
        "is_active": True,
    },
    {
        "name_uz": "Jizzax",
        "name_ru": "Джизак",
        "name_en": "Jizzakh",
        "center_latitude": 40.1158,
        "center_longitude": 67.8422,
        "display_order": 6,
        "is_active": True,
    },
    {
        "name_uz": "Qashqadaryo",
        "name_ru": "Кашкадарья",
        "name_en": "Kashkadarya",
        "center_latitude": 38.8406,
        "center_longitude": 65.7892,
        "display_order": 7,
        "is_active": True,
    },
    {
        "name_uz": "Navoiy",
        "name_ru": "Навои",
        "name_en": "Navoi",
        "center_latitude": 40.0844,
        "center_longitude": 65.3792,
        "display_order": 8,
        "is_active": True,
    },
    {
        "name_uz": "Namangan",
        "name_ru": "Наманган",
        "name_en": "Namangan",
        "center_latitude": 40.9983,
        "center_longitude": 71.6726,
        "display_order": 9,
        "is_active": True,
    },
    {
        "name_uz": "Samarqand",
        "name_ru": "Самарканд",
        "name_en": "Samarkand",
        "center_latitude": 39.6542,
        "center_longitude": 66.9597,
        "display_order": 10,
        "is_active": True,
    },
    {
        "name_uz": "Sirdaryo",
        "name_ru": "Сырдарья",
        "name_en": "Syrdarya",
        "center_latitude": 40.8433,
        "center_longitude": 68.6617,
        "display_order": 11,
        "is_active": True,
    },
    {
        "name_uz": "Surxondaryo",
        "name_ru": "Сурхандарья",
        "name_en": "Surkhandarya",
        "center_latitude": 37.2249,
        "center_longitude": 67.2783,
        "display_order": 12,
        "is_active": True,
    },
    {
        "name_uz": "Xorazm",
        "name_ru": "Хорезм",
        "name_en": "Khorezm",
        "center_latitude": 41.5500,
        "center_longitude": 60.6333,
        "display_order": 13,
        "is_active": True,
    },
    {
        "name_uz": "Qoraqalpog'iston",
        "name_ru": "Каракалпакстан",
        "name_en": "Karakalpakstan",
        "center_latitude": 42.4647,
        "center_longitude": 59.6142,
        "display_order": 14,
        "is_active": True,
    },
]


def add_regions(db: Session):
    """Добавление регионов в базу данных"""
    added_count = 0
    updated_count = 0
    
    for region_data in REGIONS_DATA:
        # Проверяем, существует ли регион
        existing_region = db.query(Region).filter(
            Region.name_ru == region_data["name_ru"]
        ).first()
        
        if existing_region:
            # Обновляем существующий регион
            for key, value in region_data.items():
                setattr(existing_region, key, value)
            updated_count += 1
            print(f"Обновлен регион: {region_data['name_ru']}")
        else:
            # Создаем новый регион
            region = Region(**region_data)
            db.add(region)
            added_count += 1
            print(f"Добавлен регион: {region_data['name_ru']}")
    
    db.commit()
    print(f"\nВсего добавлено регионов: {added_count}")
    print(f"Всего обновлено регионов: {updated_count}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        add_regions(db)
        print("\nРегионы успешно добавлены в базу данных!")
    except Exception as e:
        print(f"\nОшибка при добавлении регионов: {e}")
        db.rollback()
    finally:
        db.close()

