"""
Миграция баланса из users.balance в users_extended.balance (единый баланс).
Запуск: python scripts/migrate_balance_to_extended.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.database import engine
from app.models.user import User
from app.models.user_extended import UserExtended
from app.database import SessionLocal


def main():
    db = SessionLocal()
    try:
        print("Начинаем миграцию баланса...")
        
        # Получаем всех пользователей с балансом в users
        users_with_balance = db.query(User).filter(User.balance != 0.0).all()
        print(f"Найдено пользователей с балансом в users: {len(users_with_balance)}")
        
        migrated_count = 0
        skipped_count = 0
        
        for user in users_with_balance:
            # Проверяем наличие UserExtended
            user_extended = db.query(UserExtended).filter(UserExtended.user_id == user.id).first()
            
            if not user_extended:
                print(f"⚠ Пропущен user_id={user.id}: нет UserExtended записи")
                skipped_count += 1
                continue
            
            # Если в users_extended баланс уже есть и он не равен нулю, не перезаписываем
            if user_extended.balance != 0.0:
                print(f"⚠ Пропущен user_id={user.id}: в users_extended уже есть баланс {user_extended.balance}")
                skipped_count += 1
                continue
            
            # Переносим баланс
            old_balance = user.balance
            user_extended.balance = float(user.balance)
            
            print(f"✓ user_id={user.id}: перенесён баланс {old_balance} сум")
            migrated_count += 1
        
        # Коммитим изменения
        db.commit()
        
        print(f"\n✓ Миграция завершена:")
        print(f"  - Перенесено балансов: {migrated_count}")
        print(f"  - Пропущено: {skipped_count}")
        print(f"\n⚠ ВАЖНО: Поле users.balance теперь не используется.")
        print(f"   Все операции с балансом идут через users_extended.balance")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
