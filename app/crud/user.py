from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from fastapi import HTTPException, status

from app.models.user import User, VerificationCode, BlacklistedToken
from app.models.user_extended import UserExtended
from app.services.user_service.crud import create_user_extended
from app.services.profile_service.crud import create_profile
from app.services.notifications_service.crud import create_notifications
from app.services.statistics_service.crud import create_statistics
from app.schemas.user_extended import UserExtendedCreate
from app.core.utils import get_code_expiration_time, is_code_expired


def get_user_by_phone_number(db: Session, phone_number: str) -> Optional[User]:
    """
    Получение пользователя по номеру телефона
    Защита от SQL инъекций через параметризованные запросы SQLAlchemy
    """
    return db.query(User).filter(User.phone_number == phone_number).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Получение пользователя по ID
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_login(db: Session, login: str) -> Optional[User]:
    """
    Получение пользователя по логину
    Защита от SQL инъекций через параметризованные запросы SQLAlchemy
    """
    return db.query(User).filter(User.login == login).first()


def create_user(db: Session, phone_number: str, fullname: Optional[str] = None) -> User:
    """
    Создание нового пользователя с полным профилем
    Автоматическая регистрация при первом входе
    Автоматически создает расширенный профиль со всеми связанными данными:
    - UserExtended (расширенная информация)
    - UserProfile (профиль с документами и настройками)
    - UserNotification (настройки уведомлений)
    - UserStatistics (статистика)
    """
    # Создаем основную запись пользователя
    db_user = User(
        phone_number=phone_number,
        fullname=fullname,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Создаем расширенный профиль со всеми значениями по умолчанию
    try:
        from app.services.user_service.crud import create_user_extended
        from app.services.profile_service.crud import create_profile
        from app.services.notifications_service.crud import create_notifications
        from app.services.statistics_service.crud import create_statistics
        
        # Создаем расширенную запись пользователя с значениями по умолчанию
        user_extended_data = UserExtendedCreate(
            user_id=db_user.id,
            phone=phone_number,
            name=fullname,
            email=None,  # По умолчанию None
            avatar=None,  # По умолчанию None
            language="ru",  # По умолчанию русский
            balance=0.0,  # Начальный баланс 0
            level="Новичок",  # Уровень по умолчанию
            rating=0.0  # Рейтинг по умолчанию
        )
        user_extended = create_user_extended(db, user_extended_data)
        
        # Создаем профиль с документами и настройками по умолчанию
        # create_profile уже устанавливает settings по умолчанию
        create_profile(db, user_extended.id)
        
        # Создаем настройки уведомлений по умолчанию
        # create_notifications уже устанавливает все значения по умолчанию
        create_notifications(db, user_extended.id)
        
        # Создаем статистику по умолчанию
        # create_statistics уже создает запись с нулевыми значениями
        create_statistics(db, user_extended.id)
        
        # Создаем базовые достижения для пользователя
        try:
            from app.services.achievements_service.crud import create_achievement
            from app.schemas.user_extended import UserAchievementCreate
            
            # Базовые достижения
            base_achievements = [
                UserAchievementCreate(
                    achievement_type="first_refuel",
                    icon="gas_pump",
                    title="Первая заправка",
                    description="Заправьтесь впервые",
                    color=0x2196F3  # Синий цвет
                ),
                UserAchievementCreate(
                    achievement_type="star_driver",
                    icon="star",
                    title="Звездный водитель",
                    description="50+ заправок",
                    color=0xFFC107  # Желтый цвет
                ),
                UserAchievementCreate(
                    achievement_type="lover",
                    icon="heart",
                    title="Любитель",
                    description="10+ избранных",
                    color=0xE91E63  # Розовый цвет
                ),
                UserAchievementCreate(
                    achievement_type="premium",
                    icon="badge",
                    title="Премиум",
                    description="Активируйте подписку",
                    color=0x9E9E9E  # Серый цвет
                ),
            ]
            
            for achievement_data in base_achievements:
                create_achievement(db, user_extended.id, achievement_data)
        except Exception as achievement_error:
            # Логируем ошибку, но не прерываем создание пользователя
            import traceback
            print(f"Warning: Error creating achievements for user {db_user.id}: {str(achievement_error)}")
            print(traceback.format_exc())
        
    except Exception as e:
        # Логируем ошибку детально
        import traceback
        error_details = traceback.format_exc()
        print(f"Error creating extended profile for user {db_user.id}: {str(e)}")
        print(f"Traceback: {error_details}")
        # Откатываем транзакцию, если не удалось создать полный профиль
        db.rollback()
        # Удаляем созданного пользователя, если не удалось создать полный профиль
        db.delete(db_user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании профиля пользователя: {str(e)}"
        )
    
    return db_user


def create_admin_user(
    db: Session,
    phone_number: str,
    login: str,
    hashed_password: str,
    fullname: Optional[str] = None
) -> User:
    """
    Создание пользователя-администратора с логином и паролем
    Также создает полный профиль со всеми связанными данными
    """
    db_user = User(
        phone_number=phone_number,
        fullname=fullname,
        login=login,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Создаем расширенный профиль для администратора
    try:
        # Создаем расширенную запись пользователя с значениями по умолчанию
        user_extended_data = UserExtendedCreate(
            user_id=db_user.id,
            phone=phone_number,
            name=fullname,
            email=None,
            avatar=None,
            language="ru",
            balance=0.0,
            level="Новичок",
            rating=0.0
        )
        user_extended = create_user_extended(db, user_extended_data)
        
        # Создаем профиль с документами и настройками по умолчанию
        create_profile(db, user_extended.id)
        
        # Создаем настройки уведомлений по умолчанию
        create_notifications(db, user_extended.id)
        
        # Создаем статистику по умолчанию
        create_statistics(db, user_extended.id)
        
    except Exception as e:
        # Логируем ошибку, но не удаляем администратора, так как он уже создан
        import traceback
        error_details = traceback.format_exc()
        print(f"Warning: Error creating extended profile for admin {db_user.id}: {str(e)}")
        print(f"Traceback: {error_details}")
        # Не прерываем создание администратора, так как основная функциональность уже работает
    
    return db_user


def check_login_exists(db: Session, login: str) -> bool:
    """
    Проверка существования логина
    """
    user = db.query(User).filter(User.login == login).first()
    return user is not None


def update_user(db: Session, user_id: int, fullname: Optional[str] = None) -> Optional[User]:
    """
    Обновление информации о пользователе
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    if fullname is not None:
        user.fullname = fullname
    
    db.commit()
    db.refresh(user)
    return user


# Verification Code CRUD operations

def create_verification_code(
    db: Session,
    phone_number: str,
    code: str
) -> VerificationCode:
    """
    Создание или обновление кода верификации
    Использует UPSERT для безопасности (on conflict update)
    """
    expires_at = get_code_expiration_time()
    
    # Проверяем существующий код
    existing_code = db.query(VerificationCode).filter(
        VerificationCode.phone_number == phone_number
    ).first()
    
    if existing_code:
        # Обновляем существующий код
        existing_code.code = code
        existing_code.expires_at = expires_at
        db.commit()
        db.refresh(existing_code)
        return existing_code
    else:
        # Создаем новый код
        verification_code = VerificationCode(
            phone_number=phone_number,
            code=code,
            expires_at=expires_at
        )
        db.add(verification_code)
        db.commit()
        db.refresh(verification_code)
        return verification_code


def verify_code(
    db: Session,
    phone_number: str,
    code: str
) -> Optional[VerificationCode]:
    """
    Проверка кода верификации
    Проверяет код и его срок действия
    Защита от SQL инъекций через параметризованные запросы
    """
    verification = db.query(VerificationCode).filter(
        and_(
            VerificationCode.phone_number == phone_number,
            VerificationCode.code == code
        )
    ).first()
    
    if not verification:
        return None
    
    # Проверяем срок действия кода
    if is_code_expired(verification.expires_at):
        # Удаляем истекший код
        db.delete(verification)
        db.commit()
        return None
    
    return verification


def delete_verification_code(db: Session, phone_number: str) -> bool:
    """
    Удаление кода верификации после успешной верификации
    """
    verification = db.query(VerificationCode).filter(
        VerificationCode.phone_number == phone_number
    ).first()
    
    if verification:
        db.delete(verification)
        db.commit()
        return True
    return False


_DELETED_PLACEHOLDER_PHONE = "__deleted_placeholder__"


def _get_or_create_deleted_placeholder_user(db: Session) -> User:
    """Создаёт или возвращает пользователя-заглушку для сохранения контента удалённых пользователей."""
    u = db.query(User).filter(User.phone_number == _DELETED_PLACEHOLDER_PHONE).first()
    if u:
        return u
    u = User(
        phone_number=_DELETED_PLACEHOLDER_PHONE,
        fullname="Удалённый пользователь",
        is_active=False,
        is_admin=False,
    )
    db.add(u)
    db.flush()
    return u


def _run_with_savepoint(db: Session, fn):
    """Выполняет блок в savepoint; при ошибке откатывает только его и логирует."""
    try:
        with db.begin_nested():
            fn()
            db.flush()
    except Exception as e:
        print(f"Warning in delete_user: {e}")


def delete_user(db: Session, phone_number: str) -> bool:
    """
    Удаление пользователя по номеру телефона.
    
    Персональные данные (профиль, избранное, баланс и т.п.) удаляются.
    Контент (отзывы, сообщения, заказы) сохраняется и привязывается к пользователю «Удалённый пользователь».
    """
    user = get_user_by_phone_number(db, phone_number)
    if not user:
        return False
    if user.phone_number == _DELETED_PLACEHOLDER_PHONE:
        return False  # Не удаляем заглушку

    from sqlalchemy import text

    placeholder = _get_or_create_deleted_placeholder_user(db)
    pid = placeholder.id
    uid = user.id

    try:
        # 1. users_extended и дочерние таблицы — персональные данные, удаляем
        user_extended = db.query(UserExtended).filter(UserExtended.user_id == uid).first()
        if user_extended:
            ueid = user_extended.id

            def _del_extended():
                db.execute(text("DELETE FROM user_statistics WHERE user_id = :id"), {"id": ueid})
                db.execute(text("DELETE FROM transactions WHERE user_id = :id"), {"id": ueid})
                db.execute(text("DELETE FROM user_achievements WHERE user_id = :id"), {"id": ueid})
                db.execute(text("DELETE FROM user_favorites WHERE user_id = :id"), {"id": ueid})
                db.execute(text("DELETE FROM user_profiles WHERE user_id = :id"), {"id": ueid})
                db.execute(text("DELETE FROM user_notifications WHERE user_id = :id"), {"id": ueid})
                db.execute(text("DELETE FROM users_extended WHERE id = :id"), {"id": ueid})

            _run_with_savepoint(db, _del_extended)

        # 2. Обнуляем nullable FK (только существующие колонки в моделях)
        def _null_fk():
            for table, *cols in [
                ("fuel_prices", "updated_by_user_id", "updated_by_admin_id"),
                ("gas_station_photos", "uploaded_by_user_id", "uploaded_by_admin_id"),
                ("gas_stations", "created_by_user_id", "created_by_admin_id"),
                ("car_washes", "created_by_user_id", "created_by_admin_id"),
                ("car_wash_services", "updated_by_user_id", "updated_by_admin_id"),
                ("car_wash_photos", "uploaded_by_user_id", "uploaded_by_admin_id"),
                ("electric_stations", "created_by_user_id", "created_by_admin_id"),
                ("electric_station_photos", "uploaded_by_user_id", "uploaded_by_admin_id"),
                ("restaurants", "created_by_user_id", "created_by_admin_id"),
                ("restaurant_photos", "uploaded_by_user_id", "uploaded_by_admin_id"),
                ("service_stations", "created_by_user_id", "created_by_admin_id"),
                ("service_prices", "updated_by_user_id", "updated_by_admin_id"),
                ("service_station_photos", "uploaded_by_user_id", "uploaded_by_admin_id"),
                ("advertisement_views", "user_id"),
                ("advertisement_clicks", "user_id"),
                ("delivery_orders", "canceled_by_user_id", "customer_id"),
            ]:
                for col in cols:
                    db.execute(text(f"UPDATE {table} SET {col} = NULL WHERE {col} = :uid"), {"uid": uid})

        _run_with_savepoint(db, _null_fk)

        # 3. Контент: привязываем к placeholder вместо удаления
        def _replace_with_placeholder():
            db.execute(text("UPDATE global_chat_messages SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE support_tickets SET assigned_to = NULL WHERE assigned_to = :uid"), {"uid": uid})
            db.execute(text("UPDATE support_tickets SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE support_messages SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE delivery_orders SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE user_balance_logs SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE drivers SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE reviews SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE car_wash_reviews SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE electric_station_reviews SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE restaurant_reviews SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE service_station_reviews SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE notification_read_status SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})
            db.execute(text("UPDATE notifications SET user_id = :pid WHERE user_id = :uid"), {"pid": pid, "uid": uid})

        _run_with_savepoint(db, _replace_with_placeholder)

        # 4. Удаляем связи (блокировки, скрытые сообщения пользователя)
        def _del_links():
            db.execute(text("DELETE FROM user_blocks WHERE blocker_id = :uid OR blocked_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM hidden_global_chat_messages WHERE user_id = :uid"), {"uid": uid})

        _run_with_savepoint(db, _del_links)

        # 5. Удаляем verification_codes и blacklisted_tokens
        db.query(VerificationCode).filter(VerificationCode.phone_number == phone_number).delete(synchronize_session=False)
        db.query(BlacklistedToken).filter(BlacklistedToken.user_id == uid).delete(synchronize_session=False)
        db.flush()

        # 6. Удаляем пользователя
        db.delete(user)
        db.commit()
        return True
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error deleting user {phone_number}: {str(e)}")
        print(f"Traceback: {error_details}")
        # Пробрасываем исключение дальше, чтобы эндпоинт мог его обработать
        raise


def set_admin_status(db: Session, phone_number: str, is_admin: bool) -> Optional[User]:
    """
    Установка статуса администратора для пользователя
    """
    user = get_user_by_phone_number(db, phone_number)
    if not user:
        return None
    
    user.is_admin = is_admin
    db.commit()
    db.refresh(user)
    return user


def set_block_status(db: Session, phone_number: str, is_blocked: bool) -> Optional[User]:
    """
    Блокировка/разблокировка пользователя
    """
    user = get_user_by_phone_number(db, phone_number)
    if not user:
        return None
    
    user.is_blocked = is_blocked
    # Если пользователь заблокирован, деактивируем его
    if is_blocked:
        user.is_active = False
    db.commit()
    db.refresh(user)
    return user


def add_token_to_blacklist(db: Session, token: str, user_id: Optional[int] = None) -> BlacklistedToken:
    """
    Добавление токена в черный список (отзыв токена)
    """
    blacklisted_token = BlacklistedToken(
        token=token,
        user_id=user_id
    )
    db.add(blacklisted_token)
    db.commit()
    db.refresh(blacklisted_token)
    return blacklisted_token


def is_token_blacklisted(db: Session, token: str) -> bool:
    """
    Проверка, находится ли токен в черном списке
    """
    blacklisted = db.query(BlacklistedToken).filter(BlacklistedToken.token == token).first()
    return blacklisted is not None


def has_any_admin(db: Session) -> bool:
    """
    Проверка наличия хотя бы одного администратора в базе данных
    """
    admin_count = db.query(User).filter(User.is_admin == True).count()
    return admin_count > 0


def get_all_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    is_admin: Optional[bool] = None,
    is_blocked: Optional[bool] = None,
    is_active: Optional[bool] = None
) -> Tuple[List[User], int]:
    """
    Получение списка всех пользователей с фильтрацией и пагинацией
    
    Args:
        db: Сессия базы данных
        skip: Количество записей для пропуска (для пагинации)
        limit: Максимальное количество записей для возврата
        is_admin: Фильтр по статусу администратора (None - все)
        is_blocked: Фильтр по статусу блокировки (None - все)
        is_active: Фильтр по статусу активности (None - все)
    
    Returns:
        Кортеж (список пользователей, общее количество)
    """
    query = db.query(User)
    
    # Применяем фильтры
    if is_admin is not None:
        query = query.filter(User.is_admin == is_admin)
    if is_blocked is not None:
        query = query.filter(User.is_blocked == is_blocked)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Получаем общее количество (до пагинации)
    total = query.count()
    
    # Применяем пагинацию и сортировку
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    return users, total
