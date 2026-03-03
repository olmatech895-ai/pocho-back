"""
Скрипт для импорта данных о заправках из CSV файлов в базу данных
"""
import csv
import sys
import io
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.gas_station import GasStation, FuelPrice, FuelType, StationStatus
from app.models.electric_station import ElectricStation, ChargingPoint, ConnectorType, ElectricStationStatus, ChargingPointStatus

# Создаем таблицы если их нет
Base.metadata.create_all(bind=engine)


FUEL_TYPE_MAPPING = {
    "АИ-80": FuelType.AI_80,
    "АИ-91": FuelType.AI_91,
    "АИ-95": FuelType.AI_95,
    "АИ-98": FuelType.AI_98,
    "Дизель": FuelType.DIESEL,
    "Газ": FuelType.GAS,
}

# Маппинг boolean значений из CSV
def parse_bool(value: str) -> bool:
    """Парсинг boolean значений из CSV"""
    if not value or value.strip() == "":
        return False
    return value.lower() in ["true", "1", "yes", "да"]


def parse_coordinates(coords_str: str) -> tuple[Optional[float], Optional[float]]:
    """Парсинг координат из строки формата 'latitude, longitude'"""
    if not coords_str or coords_str.strip() == "":
        return None, None
    
    try:
        # Убираем кавычки и пробелы
        coords_str = coords_str.strip().strip('"').strip("'")
        parts = coords_str.split(",")
        if len(parts) >= 2:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            return lat, lon
    except (ValueError, IndexError):
        pass
    
    return None, None


def parse_working_hours(working_hours: str) -> tuple[bool, Optional[str]]:
    """Парсинг режима работы"""
    if not working_hours or working_hours.strip() == "" or working_hours.strip().lower() == "нет информации":
        return False, None
    
    working_hours = working_hours.strip()
    
    # Проверяем на 24/7
    if "24/7" in working_hours.lower() or "24 соат" in working_hours.lower() or "24 часа" in working_hours.lower():
        return True, None
    
    return False, working_hours


def parse_phone(phone: str) -> Optional[str]:
    """Парсинг номера телефона"""
    if not phone or phone.strip() == "" or phone.strip().lower() == "нет информации":
        return None
    return phone.strip()


def load_csv_data(places_file: str, prices_file: str) -> tuple[Dict, Dict]:
    """Загрузка данных из CSV файлов"""
    places_data = {}
    prices_data = {}
    
    # Загружаем данные о местах
    with open(places_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_id = row.get('🔒 Row ID', '').strip()
            if row_id:
                places_data[row_id] = row
    
    # Загружаем данные о ценах
    with open(prices_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            station_id = row.get('stationID', '').strip()
            if station_id:
                if station_id not in prices_data:
                    prices_data[station_id] = []
                prices_data[station_id].append(row)
    
    return places_data, prices_data


def import_gas_stations(db: Session, places_data: Dict, prices_data: Dict) -> Dict[str, int]:
    """Импорт заправок в базу данных.

    Возвращает маппинг Row ID (из togo-places.csv) -> ID заправки в БД.
    Этот маппинг затем используется для импорта комментариев.
    """
    imported_count = 0
    skipped_count = 0
    error_count = 0
    row_id_to_station_id: Dict[str, int] = {}
    
    # Получаем первого админа для created_by_admin_id
    from app.models.user import User
    admin = db.query(User).filter(User.is_admin == True).first()
    admin_id = admin.id if admin else None
    
    if not admin_id:
        print("ВНИМАНИЕ: Не найден администратор. Заправки будут созданы без created_by_admin_id")
    
    for row_id, place in places_data.items():
        try:
            # Пропускаем если это не АЗС
            category = place.get('category', '').strip()
            if category != 'АЗС':
                continue
            
            # Проверяем, есть ли уже заправка с таким Row ID (можно использовать name + coordinates)
            name = place.get('name', '').strip()
            if not name:
                skipped_count += 1
                continue
            
            # Парсим координаты
            coords_str = place.get('coordinates', '').strip()
            latitude, longitude = parse_coordinates(coords_str)
            
            if latitude is None or longitude is None:
                print(f"Пропущена заправка '{name}': нет координат")
                skipped_count += 1
                continue
            
            # Проверяем, существует ли уже заправка с такими координатами
            existing = db.query(GasStation).filter(
                GasStation.latitude == latitude,
                GasStation.longitude == longitude
            ).first()
            
            if existing:
                print(f"Пропущена заправка '{name}': уже существует (ID: {existing.id})")
                skipped_count += 1
                # Сохраняем связь Row ID -> ID существующей заправки
                row_id_to_station_id[row_id] = existing.id
                # Обновляем цены для существующей заправки
                if row_id in prices_data:
                    update_fuel_prices(db, existing.id, prices_data[row_id], admin_id)
                continue
            
            # Парсим режим работы
            working_hours_str = place.get('working_hours', '').strip()
            is_24_7, working_hours = parse_working_hours(working_hours_str)
            
            # Создаем заправку
            gas_station = GasStation(
                name=name,
                address=place.get('address', '').strip() or name,
                latitude=latitude,
                longitude=longitude,
                phone=parse_phone(place.get('phone_number', '').strip()),
                is_24_7=is_24_7,
                working_hours=working_hours,
                status=StationStatus.APPROVED,  # Сразу одобряем импортированные
                created_by_admin_id=admin_id,
                category="Заправка"
            )
            
            db.add(gas_station)
            db.flush()  # Получаем ID

            # Сохраняем связь Row ID -> ID созданной заправки
            row_id_to_station_id[row_id] = gas_station.id
            
            # Добавляем цены на топливо
            if row_id in prices_data:
                add_fuel_prices(db, gas_station.id, prices_data[row_id], admin_id)
            
            # Также проверяем поля из CSV для типов топлива
            add_fuel_prices_from_csv_columns(db, gas_station.id, place, admin_id)
            
            imported_count += 1
            
            if imported_count % 10 == 0:
                print(f"Импортировано {imported_count} заправок...")
                db.commit()
        
        except Exception as e:
            error_count += 1
            print(f"Ошибка при импорте заправки '{place.get('name', 'Unknown')}': {str(e)}")
            db.rollback()
            continue
    
    db.commit()
    print(f"\nИмпорт заправок завершен:")
    print(f"   - Импортировано: {imported_count}")
    print(f"   - Пропущено: {skipped_count}")
    print(f"   - Ошибок: {error_count}")

    return row_id_to_station_id


def add_fuel_prices(db: Session, station_id: int, prices: List[Dict], admin_id: Optional[int]):
    """Добавление цен на топливо из данных о ценах"""
    # Собираем все цены по типам топлива, берем последнюю (самую актуальную)
    prices_by_type = {}
    for price_row in prices:
        fuel_type_str = price_row.get('fuel_type', '').strip()
        price_str = price_row.get('price', '').strip()
        
        if not fuel_type_str or not price_str:
            continue
        
        try:
            price = float(price_str)
            prices_by_type[fuel_type_str] = price  # Перезаписываем, если есть дубликаты
        except ValueError:
            continue
    
    # Добавляем/обновляем цены
    for fuel_type_str, price in prices_by_type.items():
        try:
            # Маппим тип топлива
            fuel_type = FUEL_TYPE_MAPPING.get(fuel_type_str)
            if not fuel_type:
                # Пропускаем типы, которых нет в модели (АИ-92, Метан, Пропан)
                continue
            
            # Проверяем, есть ли уже такая цена
            existing = db.query(FuelPrice).filter(
                FuelPrice.gas_station_id == station_id,
                FuelPrice.fuel_type == fuel_type
            ).first()
            
            if existing:
                # Обновляем цену
                existing.price = price
                existing.updated_by_admin_id = admin_id
            else:
                # Создаем новую цену
                fuel_price = FuelPrice(
                    gas_station_id=station_id,
                    fuel_type=fuel_type,
                    price=price,
                    updated_by_admin_id=admin_id
                )
                db.add(fuel_price)
        
        except Exception as e:
            print(f"Ошибка при добавлении цены {fuel_type_str}: {str(e)}")
            continue


def add_fuel_prices_from_csv_columns(db: Session, station_id: int, place: Dict, admin_id: Optional[int]):
    """Добавление цен на топливо из колонок CSV (ai-80, ai-92 и т.д.)"""
    # Маппинг колонок CSV на типы топлива (только те, что есть в модели)
    # АИ-92 нет в модели, пропускаем
    column_mapping = {
        'ai-80': FuelType.AI_80,
        'ai-91': FuelType.AI_91,
        'ai-95': FuelType.AI_95,
        'ai-98': FuelType.AI_98,
        'diesel': FuelType.DIESEL,
        'gas': FuelType.GAS,
    }
    
    # Просто проверяем наличие, цены добавляются из prices_data
    # Эта функция может использоваться для логирования или будущих улучшений


def update_fuel_prices(db: Session, station_id: int, prices: List[Dict], admin_id: Optional[int]):
    """Обновление цен на топливо для существующей заправки"""
    add_fuel_prices(db, station_id, prices, admin_id)


def import_electric_stations(db: Session, places_data: Dict):
    """Импорт электрозаправок в базу данных"""
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    # Получаем первого админа
    from app.models.user import User
    admin = db.query(User).filter(User.is_admin == True).first()
    admin_id = admin.id if admin else None
    
    for row_id, place in places_data.items():
        try:
            # Проверяем, есть ли электрозарядка
            electric_charging = parse_bool(place.get('electric_charging', ''))
            if not electric_charging:
                continue
            
            # Пропускаем если это не АЗС (но может быть электрозаправка)
            category = place.get('category', '').strip()
            
            name = place.get('name', '').strip()
            if not name:
                skipped_count += 1
                continue
            
            # Парсим координаты
            coords_str = place.get('coordinates', '').strip()
            latitude, longitude = parse_coordinates(coords_str)
            
            if latitude is None or longitude is None:
                print(f"Пропущена электрозаправка '{name}': нет координат")
                skipped_count += 1
                continue
            
            # Проверяем, существует ли уже электрозаправка с такими координатами
            existing = db.query(ElectricStation).filter(
                ElectricStation.latitude == latitude,
                ElectricStation.longitude == longitude
            ).first()
            
            if existing:
                print(f"Пропущена электрозаправка '{name}': уже существует (ID: {existing.id})")
                skipped_count += 1
                continue
            
            # Парсим режим работы
            working_hours_str = place.get('working_hours', '').strip()
            is_24_7, working_hours = parse_working_hours(working_hours_str)
            
            # Создаем электрозаправку
            electric_station = ElectricStation(
                name=name,
                address=place.get('address', '').strip() or name,
                latitude=latitude,
                longitude=longitude,
                phone=parse_phone(place.get('phone_number', '').strip()),
                is_24_7=is_24_7,
                working_hours=working_hours,
                has_parking=parse_bool(place.get('parking', '')),
                has_cafe=parse_bool(place.get('cafe', '')),
                has_waiting_room=True,  # По умолчанию
                has_restroom=parse_bool(place.get('wc', '')),
                accepts_cards=True,  # По умолчанию
                status=ElectricStationStatus.APPROVED,
                created_by_admin_id=admin_id,
                category="Электрозаправка"
            )
            
            db.add(electric_station)
            db.flush()
            
            # Добавляем зарядную точку по умолчанию (Type 2, 50 кВт)
            charging_point = ChargingPoint(
                electric_station_id=electric_station.id,
                connector_type=ConnectorType.TYPE_2,
                power_kw=50.0,
                status=ChargingPointStatus.AVAILABLE
            )
            db.add(charging_point)
            
            # Обновляем счетчики
            electric_station.total_points = 1
            electric_station.available_points = 1
            
            imported_count += 1
            
            if imported_count % 5 == 0:
                print(f"Импортировано {imported_count} электрозаправок...")
                db.commit()
        
        except Exception as e:
            error_count += 1
            print(f"Ошибка при импорте электрозаправки '{place.get('name', 'Unknown')}': {str(e)}")
            db.rollback()
            continue
    
    db.commit()
    print(f"\nИмпорт электрозаправок завершен:")
    print(f"   - Импортировано: {imported_count}")
    print(f"   - Пропущено: {skipped_count}")
    print(f"   - Ошибок: {error_count}")


def import_comments(db: Session, comments_file: str, row_id_to_station_id: Dict[str, int]):
    """Импорт комментариев из CSV в таблицу отзывов (reviews).

    CSV: togo-comments.csv
    Колонки: User Email, Time, Message, page_Id
    page_Id соответствует значению '🔒 Row ID' в togo-places.csv.
    """
    from app.models.user import User
    from app.models.gas_station import Review

    imported_count = 0
    skipped_count = 0
    error_count = 0

    # Кэш, чтобы не дергать БД для каждого письма
    email_user_cache: Dict[str, int] = {}

    def get_or_create_user_for_email(email: str) -> int:
        """Возвращает ID пользователя для email, создавая виртуального при необходимости."""
        nonlocal email_user_cache

        email = (email or "").strip()
        cache_key = email or "__empty_email__"

        if cache_key in email_user_cache:
            return email_user_cache[cache_key]

        user = None
        if email:
            user = db.query(User).filter(User.login == email).first()

        if not user:
            # Генерируем уникальный логин и "телефон" для виртуального пользователя
            base_login = email or "togo_user"
            login = base_login
            suffix = 1
            while db.query(User).filter(User.login == login).first():
                suffix += 1
                login = f"{base_login}_{suffix}"

            phone_number = f"virtual_{login}"

            user = User(
                phone_number=phone_number,
                fullname=email or "TOGO User",
                login=login,
                is_admin=False,
            )
            db.add(user)
            db.flush()

        email_user_cache[cache_key] = user.id
        return user.id

    if not Path(comments_file).exists():
        print(f"Файл с комментариями не найден: {comments_file}")
        return

    print(f"Загрузка комментариев из: {comments_file}")

    with open(comments_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                page_id = (row.get("page_Id") or row.get("stationID") or "").strip()
                if not page_id:
                    skipped_count += 1
                    continue

                gas_station_id = row_id_to_station_id.get(page_id)
                if not gas_station_id:
                    # Нет соответствующей заправки в БД
                    skipped_count += 1
                    continue

                email = (row.get("User Email") or "").strip()
                message = (row.get("Message") or "").strip()
                time_str = (row.get("Time") or "").strip()

                if not message:
                    skipped_count += 1
                    continue

                user_id = get_or_create_user_for_email(email)

                # Проверяем, есть ли уже отзыв от этого пользователя на эту заправку
                existing = (
                    db.query(Review)
                    .filter(
                        Review.gas_station_id == gas_station_id,
                        Review.user_id == user_id,
                    )
                    .first()
                )

                # Собираем текст с сохранением email и времени
                comment_text = message
                if email or time_str:
                    meta_parts = []
                    if email:
                        meta_parts.append(f"email: {email}")
                    if time_str:
                        meta_parts.append(f"time: {time_str}")
                    meta = ", ".join(meta_parts)
                    comment_text = f"{message}\n\n({meta})"

                if existing:
                    # Если отзыв уже есть, просто дополняем его текст
                    existing.comment = (existing.comment or "") + "\n\n---\n\n" + comment_text
                else:
                    review = Review(
                        gas_station_id=gas_station_id,
                        user_id=user_id,
                        rating=5,  # По умолчанию считаем оценку 5
                        comment=comment_text,
                    )
                    db.add(review)

                imported_count += 1
                if imported_count % 20 == 0:
                    db.commit()

            except Exception as e:
                error_count += 1
                print(f"Ошибка при импорте комментария: {str(e)}")
                db.rollback()
                continue

    db.commit()

    print(f"\nИмпорт комментариев завершен:")
    print(f"   - Импортировано/обновлено: {imported_count}")
    print(f"   - Пропущено: {skipped_count}")
    print(f"   - Ошибок: {error_count}")


def main():
    """Основная функция импорта"""
    base_dir = Path(__file__).parent
    places_file = base_dir / "data" / "togo-places.csv"
    prices_file = base_dir / "data" / "togp-fuel-price.csv"
    comments_file = base_dir / "data" / "togo-comments.csv"
    
    if not places_file.exists():
        print(f"Файл не найден: {places_file}")
        return
    
    if not prices_file.exists():
        print(f"Файл не найден: {prices_file}")
        return
    
    print("Загрузка данных из CSV файлов...")
    places_data, prices_data = load_csv_data(str(places_file), str(prices_file))
    print(f"Загружено {len(places_data)} мест и {sum(len(prices) for prices in prices_data.values())} цен")
    
    db = SessionLocal()
    try:
        print("\nИмпорт заправок...")
        row_id_to_station_id = import_gas_stations(db, places_data, prices_data)
        
        print("\nИмпорт электрозаправок...")
        import_electric_stations(db, places_data)

        if comments_file.exists():
            print("\nИмпорт комментариев...")
            import_comments(db, str(comments_file), row_id_to_station_id)
        else:
            print(f"\nФайл с комментариями не найден, импорт комментариев пропущен: {comments_file}")
        
        print("\nИмпорт завершен успешно!")
    
    except Exception as e:
        print(f"\nКритическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()

