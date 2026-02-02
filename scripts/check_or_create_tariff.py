"""
Проверка наличия активного тарифа доставки и создание тестового, если его нет.
Запуск: python scripts/check_or_create_tariff.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.delivery import DeliveryTariff
from app.services.delivery_service.tariff_crud import create_tariff
from app.schemas.delivery import DeliveryTariffCreate


def main():
    db: Session = SessionLocal()
    try:
        # Проверяем наличие активного тарифа
        active_tariff = db.query(DeliveryTariff).filter(DeliveryTariff.is_active == True).first()
        
        if active_tariff:
            print(f"✓ Найден активный тариф: ID={active_tariff.id}, название='{active_tariff.name}'")
            print(f"  Параметры: cost_per_km={active_tariff.cost_per_km}, min_total={active_tariff.min_total}, base_fixed={active_tariff.base_fixed}")
        else:
            print("⚠ Активный тариф не найден. Создаю тестовый тариф...")
            
            # Создаём тестовый тариф
            tariff_data = DeliveryTariffCreate(
                name="Базовый тариф",
                cost_per_km=1000.0,  # 1000 сум за км
                min_total=5000.0,     # Минимум 5000 сум
                base_fixed=2000.0,    # Базовая стоимость 2000 сум
                is_active=True
            )
            
            tariff = create_tariff(db, tariff_data)
            print(f"✓ Создан тестовый тариф: ID={tariff.id}, название='{tariff.name}'")
            print(f"  Параметры: cost_per_km={tariff.cost_per_km}, min_total={tariff.min_total}, base_fixed={tariff.base_fixed}")
        
        # Показываем все тарифы
        all_tariffs = db.query(DeliveryTariff).all()
        print(f"\nВсего тарифов в БД: {len(all_tariffs)}")
        for t in all_tariffs:
            status = "активен" if t.is_active else "неактивен"
            print(f"  - ID={t.id}, название='{t.name}', статус={status}")
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
