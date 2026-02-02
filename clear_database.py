"""
Script to clear all tables in the database
WARNING: This will delete ALL data from the database!
"""
import sys
import os
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import (
    User, VerificationCode, BlacklistedToken,
    UserExtended, UserProfile, UserFavorite,
    UserAchievement, UserNotification, Transaction, UserStatistics
)

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def clear_all_tables():
    """Удаление всех записей из всех таблиц"""
    db = SessionLocal()
    try:
        print("Starting database cleanup...")
        
        # Order of deletion is important due to foreign keys
        # First delete child tables, then parent tables
        
        tables_to_clear = [
            "user_statistics",
            "transactions",
            "user_achievements",
            "user_favorites",
            "user_profiles",
            "user_notifications",
            "users_extended",
            "blacklisted_tokens",
            "verification_codes",
            "users"
        ]
        
        # Disable foreign key checks temporarily (for PostgreSQL)
        try:
            db.execute(text("SET session_replication_role = 'replica';"))
        except Exception:
            # If command not supported (e.g., not PostgreSQL), continue
            pass
        
        for table in tables_to_clear:
            try:
                result = db.execute(text(f"DELETE FROM {table}"))
                count = result.rowcount
                print(f"[OK] Deleted {count} records from table {table}")
            except Exception as e:
                print(f"[WARNING] Error deleting from {table}: {str(e)}")
                # Continue with other tables
        
        # Re-enable foreign key checks
        try:
            db.execute(text("SET session_replication_role = 'origin';"))
        except Exception:
            pass
        
        db.commit()
        
        print("\n[SUCCESS] Database successfully cleared!")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error clearing database: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    # Если передан аргумент --yes, пропускаем подтверждение
    if len(sys.argv) > 1 and sys.argv[1] == '--yes':
        clear_all_tables()
    else:
        print("=" * 60)
        print("WARNING: This script will delete ALL data from the database!")
        print("=" * 60)
        
        try:
            response = input("\nAre you sure you want to continue? (yes/no): ")
            
            if response.lower() in ['yes', 'y']:
                clear_all_tables()
            else:
                print("Operation cancelled.")
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
            sys.exit(0)

