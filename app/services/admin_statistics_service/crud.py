"""
CRUD операции для статистики администратора
"""
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, extract
from sqlalchemy.sql import label

from app.models.user import User
from app.models.user_extended import UserExtended, Transaction
from app.models.gas_station import GasStation, StationStatus
from app.models.restaurant import Restaurant, RestaurantStatus
from app.models.service_station import ServiceStation, ServiceStationStatus
from app.models.car_wash import CarWash, CarWashStatus
from app.models.electric_station import ElectricStation, ElectricStationStatus
from app.schemas.admin_statistics import (
    KPIsResponse, KPIValue,
    CategoryMetricsResponse, CategoryMetric,
    RevenueChartResponse, NewUsersChartResponse, UserActivityChartResponse,
    CategoryDistributionResponse, CategoryDistributionItem,
    LatestTransactionsResponse, TransactionListItem,
    CategoryCompletenessResponse, CategoryCompletenessItem,
    RecentActionsResponse, RecentAction,
    OrderStatisticsResponse, OrderStatusStat,
    SystemActivityResponse
)


def get_date_range(start_date: Optional[datetime], end_date: Optional[datetime], period_days: int = 7) -> Tuple[datetime, datetime]:
    """Получение диапазона дат"""
    if end_date is None:
        end_date = datetime.utcnow()
    if start_date is None:
        start_date = end_date - timedelta(days=period_days)
    return start_date, end_date


def calculate_change_percent(current: float, previous: float) -> Optional[float]:
    """Расчет процента изменения"""
    if previous == 0:
        return None if current == 0 else 100.0
    return ((current - previous) / previous) * 100


# ==================== KPIs ====================

def get_kpis(db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, period_days: int = 7) -> KPIsResponse:
    """Получение основных KPI"""
    start_date, end_date = get_date_range(start_date, end_date, period_days)
    previous_start = start_date - (end_date - start_date)
    
    # Всего пользователей
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_users_previous = db.query(func.count(User.id)).filter(
        User.created_at < previous_start
    ).scalar() or 0
    total_users_period = db.query(func.count(User.id)).filter(
        User.created_at >= start_date,
        User.created_at <= end_date
    ).scalar() or 0
    
    # Активные пользователи (за период) - используем left join для пользователей без UserExtended
    active_users = db.query(func.count(func.distinct(User.id))).outerjoin(
        UserExtended, User.id == UserExtended.user_id
    ).filter(
        User.is_active == True,
        User.is_blocked == False,
        or_(
            UserExtended.updated_at >= start_date,
            UserExtended.id == None  # Пользователи без UserExtended считаем активными если они активны
        )
    ).scalar() or 0
    
    active_users_previous = db.query(func.count(func.distinct(User.id))).outerjoin(
        UserExtended, User.id == UserExtended.user_id
    ).filter(
        User.is_active == True,
        User.is_blocked == False,
        or_(
            and_(
                UserExtended.updated_at >= previous_start,
                UserExtended.updated_at < start_date
            ),
            UserExtended.id == None
        )
    ).scalar() or 0
    
    active_users_period = db.query(func.count(func.distinct(User.id))).outerjoin(
        UserExtended, User.id == UserExtended.user_id
    ).filter(
        User.is_active == True,
        User.is_blocked == False,
        or_(
            and_(
                UserExtended.updated_at >= start_date,
                UserExtended.updated_at <= end_date
            ),
            UserExtended.id == None
        )
    ).scalar() or 0
    
    # Всего запросов (транзакций)
    total_requests = db.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).scalar() or 0
    
    total_requests_previous = db.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= previous_start,
        Transaction.created_at < start_date
    ).scalar() or 0
    
    total_requests_period = total_requests
    
    # Выручка
    revenue = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date,
        Transaction.amount > 0
    ).scalar() or 0.0
    
    revenue_previous = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.created_at >= previous_start,
        Transaction.created_at < start_date,
        Transaction.amount > 0
    ).scalar() or 0.0
    
    revenue_period = revenue
    
    return KPIsResponse(
        total_users=KPIValue(
            value=float(total_users),
            change_percent=calculate_change_percent(total_users, total_users_previous),
            change_value=float(total_users - total_users_previous),
            period_value=float(total_users_period)
        ),
        active_users=KPIValue(
            value=float(active_users),
            change_percent=calculate_change_percent(active_users, active_users_previous),
            change_value=float(active_users - active_users_previous),
            period_value=float(active_users_period)
        ),
        total_requests=KPIValue(
            value=float(total_requests),
            change_percent=calculate_change_percent(total_requests, total_requests_previous),
            change_value=float(total_requests - total_requests_previous),
            period_value=float(total_requests_period)
        ),
        revenue=KPIValue(
            value=float(revenue),
            change_percent=calculate_change_percent(revenue, revenue_previous),
            change_value=float(revenue - revenue_previous),
            period_value=float(revenue_period)
        )
    )


# ==================== Category Metrics ====================

def get_category_metrics(db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> CategoryMetricsResponse:
    """Получение метрик по категориям"""
    start_date, end_date = get_date_range(start_date, end_date)
    previous_start = start_date - (end_date - start_date)
    
    # Заправки
    gas_total = db.query(func.count(GasStation.id)).scalar() or 0
    gas_active = db.query(func.count(GasStation.id)).filter(
        GasStation.status == StationStatus.APPROVED
    ).scalar() or 0
    gas_change = db.query(func.count(GasStation.id)).filter(
        GasStation.created_at >= start_date,
        GasStation.created_at <= end_date
    ).scalar() or 0
    
    # Рестораны
    restaurant_total = db.query(func.count(Restaurant.id)).scalar() or 0
    restaurant_active = db.query(func.count(Restaurant.id)).filter(
        Restaurant.status == RestaurantStatus.APPROVED
    ).scalar() or 0
    restaurant_change = db.query(func.count(Restaurant.id)).filter(
        Restaurant.created_at >= start_date,
        Restaurant.created_at <= end_date
    ).scalar() or 0
    
    # СТО
    service_total = db.query(func.count(ServiceStation.id)).scalar() or 0
    service_active = db.query(func.count(ServiceStation.id)).filter(
        ServiceStation.status == ServiceStationStatus.APPROVED
    ).scalar() or 0
    service_change = db.query(func.count(ServiceStation.id)).filter(
        ServiceStation.created_at >= start_date,
        ServiceStation.created_at <= end_date
    ).scalar() or 0
    
    # Автомойки
    car_wash_total = db.query(func.count(CarWash.id)).scalar() or 0
    car_wash_active = db.query(func.count(CarWash.id)).filter(
        CarWash.status == CarWashStatus.APPROVED
    ).scalar() or 0
    car_wash_change = db.query(func.count(CarWash.id)).filter(
        CarWash.created_at >= start_date,
        CarWash.created_at <= end_date
    ).scalar() or 0
    
    # Электрозаправки
    electric_total = db.query(func.count(ElectricStation.id)).scalar() or 0
    electric_active = db.query(func.count(ElectricStation.id)).filter(
        ElectricStation.status == ElectricStationStatus.APPROVED
    ).scalar() or 0
    electric_change = db.query(func.count(ElectricStation.id)).filter(
        ElectricStation.created_at >= start_date,
        ElectricStation.created_at <= end_date
    ).scalar() or 0
    
    return CategoryMetricsResponse(
        gas_stations=CategoryMetric(total=gas_total, active=gas_active, change=gas_change),
        restaurants=CategoryMetric(total=restaurant_total, active=restaurant_active, change=restaurant_change),
        service_stations=CategoryMetric(total=service_total, active=service_active, change=service_change),
        car_washes=CategoryMetric(total=car_wash_total, active=car_wash_active, change=car_wash_change),
        electric_stations=CategoryMetric(total=electric_total, active=electric_active, change=electric_change)
    )


# ==================== Charts ====================

def get_revenue_chart(db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, period_days: int = 7) -> RevenueChartResponse:
    """График выручки"""
    start_date, end_date = get_date_range(start_date, end_date, period_days)
    
    # Группируем по дням или часам в зависимости от периода
    if (end_date - start_date).days <= 1:
        # По часам
        group_by = extract('hour', Transaction.created_at)
        labels = [f"{i}ч" for i in range(24)]
        period_keys = list(range(24))
    else:
        # По дням
        group_by = func.date(Transaction.created_at)
        days = (end_date - start_date).days + 1
        labels = [f"{i}д" for i in range(1, days + 1)]
        # Генерируем список дат для ключей
        period_keys = [(start_date + timedelta(days=i)).date() for i in range(days)]
    
    # Выручка
    revenue_data = db.query(
        group_by.label('period'),
        func.coalesce(func.sum(Transaction.amount), 0).label('revenue'),
        func.count(Transaction.id).label('orders')
    ).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date,
        Transaction.amount > 0
    ).group_by(group_by).all()
    
    # Создаем словари для быстрого доступа
    revenue_dict = {row.period: row.revenue for row in revenue_data}
    orders_dict = {row.period: row.orders for row in revenue_data}
    
    # Заполняем массивы, сопоставляя ключи с метками
    revenue = []
    orders = []
    for key in period_keys:
        revenue.append(float(revenue_dict.get(key, 0)))
        orders.append(int(orders_dict.get(key, 0)))
    
    return RevenueChartResponse(
        labels=labels,
        revenue=revenue,
        orders=orders
    )


def get_new_users_chart(db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, period_days: int = 7) -> NewUsersChartResponse:
    """График новых пользователей"""
    start_date, end_date = get_date_range(start_date, end_date, period_days)
    
    if (end_date - start_date).days <= 1:
        group_by = extract('hour', User.created_at)
        labels = [f"{i}ч" for i in range(24)]
        period_keys = list(range(24))
    else:
        group_by = func.date(User.created_at)
        days = (end_date - start_date).days + 1
        labels = [f"{i}д" for i in range(1, days + 1)]
        period_keys = [(start_date + timedelta(days=i)).date() for i in range(days)]
    
    users_data = db.query(
        group_by.label('period'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date,
        User.created_at <= end_date
    ).group_by(group_by).all()
    
    users_dict = {row.period: row.count for row in users_data}
    users = [int(users_dict.get(key, 0)) for key in period_keys]
    
    return NewUsersChartResponse(
        labels=labels,
        users=users
    )


def get_user_activity_chart(db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> UserActivityChartResponse:
    """График активности пользователей"""
    start_date, end_date = get_date_range(start_date, end_date)
    
    # Группируем по часам дня
    activity_data = db.query(
        extract('hour', Transaction.created_at).label('hour'),
        func.count(func.distinct(Transaction.user_id)).label('activity')
    ).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).group_by(extract('hour', Transaction.created_at)).all()
    
    # Создаем массив для 24 часов
    activity_dict = {row.hour: row.activity for row in activity_data}
    labels = [f"{i:02d}:00" for i in range(24)]
    activity = [int(activity_dict.get(i, 0)) for i in range(24)]
    
    return UserActivityChartResponse(
        labels=labels,
        activity=activity
    )


def get_category_distribution(db: Session) -> CategoryDistributionResponse:
    """Распределение по категориям"""
    gas_count = db.query(func.count(GasStation.id)).filter(
        GasStation.status == StationStatus.APPROVED
    ).scalar() or 0
    
    restaurant_count = db.query(func.count(Restaurant.id)).filter(
        Restaurant.status == RestaurantStatus.APPROVED
    ).scalar() or 0
    
    service_count = db.query(func.count(ServiceStation.id)).filter(
        ServiceStation.status == ServiceStationStatus.APPROVED
    ).scalar() or 0
    
    car_wash_count = db.query(func.count(CarWash.id)).filter(
        CarWash.status == CarWashStatus.APPROVED
    ).scalar() or 0
    
    electric_count = db.query(func.count(ElectricStation.id)).filter(
        ElectricStation.status == ElectricStationStatus.APPROVED
    ).scalar() or 0
    
    total = gas_count + restaurant_count + service_count + car_wash_count + electric_count
    
    categories = []
    if total > 0:
        categories = [
            CategoryDistributionItem(
                category="Рестораны",
                count=restaurant_count,
                percentage=(restaurant_count / total) * 100,
                color="#ef4444"
            ),
            CategoryDistributionItem(
                category="Заправки",
                count=gas_count,
                percentage=(gas_count / total) * 100,
                color="#ec4899"
            ),
            CategoryDistributionItem(
                category="СТО",
                count=service_count,
                percentage=(service_count / total) * 100,
                color="#10b981"
            ),
            CategoryDistributionItem(
                category="Автомойки",
                count=car_wash_count,
                percentage=(car_wash_count / total) * 100,
                color="#06b6d4"
            ),
            CategoryDistributionItem(
                category="Электрозаправки",
                count=electric_count,
                percentage=(electric_count / total) * 100,
                color="#3b82f6"
            )
        ]
    
    return CategoryDistributionResponse(categories=categories)


# ==================== Transactions ====================

def get_latest_transactions(db: Session, limit: int = 5) -> LatestTransactionsResponse:
    """Последние транзакции"""
    transactions = db.query(Transaction).join(
        UserExtended, Transaction.user_id == UserExtended.id
    ).order_by(
        Transaction.created_at.desc()
    ).limit(limit).all()
    
    transaction_list = []
    for t in transactions:
        user_extended = db.query(UserExtended).filter(UserExtended.id == t.user_id).first()
        # Определяем тип категории из extra_data
        category_type = "Другое"
        if t.extra_data:
            if "gas_station_id" in t.extra_data:
                category_type = "Заправки"
            elif "restaurant_id" in t.extra_data:
                category_type = "Рестораны"
            elif "service_station_id" in t.extra_data:
                category_type = "СТО"
            elif "car_wash_id" in t.extra_data:
                category_type = "Автомойки"
            elif "electric_station_id" in t.extra_data:
                category_type = "Электрозаправки"
        
        # Определяем статус
        status = "Завершено"
        if t.type in ["pending", "processing"]:
            status = "В обработке"
        elif t.type in ["cancelled", "refunded"]:
            status = "Отменено"
        
        transaction_list.append(TransactionListItem(
            id=t.id,
            user_name=user_extended.name if user_extended else "Неизвестно",
            user_phone=user_extended.phone if user_extended else "",
            type=category_type,
            amount=abs(t.amount),
            status=status,
            created_at=t.created_at
        ))
    
    total = db.query(func.count(Transaction.id)).scalar() or 0
    
    return LatestTransactionsResponse(
        transactions=transaction_list,
        total=total
    )


# ==================== Category Completeness ====================

def get_category_completeness(db: Session) -> CategoryCompletenessResponse:
    """Заполненность категорий"""
    # Целевые значения (можно сделать настраиваемыми)
    targets = {
        "Заправки": 150,
        "Рестораны": 100,
        "СТО": 60,
        "Автомойки": 80,
        "Электрозаправки": 40
    }
    
    gas_current = db.query(func.count(GasStation.id)).filter(
        GasStation.status == StationStatus.APPROVED
    ).scalar() or 0
    
    restaurant_current = db.query(func.count(Restaurant.id)).filter(
        Restaurant.status == RestaurantStatus.APPROVED
    ).scalar() or 0
    
    service_current = db.query(func.count(ServiceStation.id)).filter(
        ServiceStation.status == ServiceStationStatus.APPROVED
    ).scalar() or 0
    
    car_wash_current = db.query(func.count(CarWash.id)).filter(
        CarWash.status == CarWashStatus.APPROVED
    ).scalar() or 0
    
    electric_current = db.query(func.count(ElectricStation.id)).filter(
        ElectricStation.status == ElectricStationStatus.APPROVED
    ).scalar() or 0
    
    categories = [
        CategoryCompletenessItem(
            category="Заправки",
            current=gas_current,
            target=targets["Заправки"],
            percentage=(gas_current / targets["Заправки"]) * 100 if targets["Заправки"] > 0 else 0
        ),
        CategoryCompletenessItem(
            category="Рестораны",
            current=restaurant_current,
            target=targets["Рестораны"],
            percentage=(restaurant_current / targets["Рестораны"]) * 100 if targets["Рестораны"] > 0 else 0
        ),
        CategoryCompletenessItem(
            category="СТО",
            current=service_current,
            target=targets["СТО"],
            percentage=(service_current / targets["СТО"]) * 100 if targets["СТО"] > 0 else 0
        ),
        CategoryCompletenessItem(
            category="Автомойки",
            current=car_wash_current,
            target=targets["Автомойки"],
            percentage=(car_wash_current / targets["Автомойки"]) * 100 if targets["Автомойки"] > 0 else 0
        ),
        CategoryCompletenessItem(
            category="Электрозаправки",
            current=electric_current,
            target=targets["Электрозаправки"],
            percentage=(electric_current / targets["Электрозаправки"]) * 100 if targets["Электрозаправки"] > 0 else 0
        )
    ]
    
    return CategoryCompletenessResponse(categories=categories)


# ==================== Recent Actions ====================

def get_recent_actions(db: Session, limit: int = 5) -> RecentActionsResponse:
    """Последние действия"""
    # Собираем действия из разных источников
    actions = []
    
    # Новые пользователи
    new_users = db.query(User).order_by(User.created_at.desc()).limit(limit * 2).all()
    for user in new_users:
        time_ago = get_time_ago(user.created_at)
        actions.append(RecentAction(
            id=user.id,
            action_type="user_registered",
            description=f"Новый пользователь зарегистрирован: {user.fullname or user.phone_number}",
            created_at=user.created_at,
            time_ago=time_ago
        ))
    
    # Новые заправки
    new_stations = db.query(GasStation).order_by(GasStation.created_at.desc()).limit(limit * 2).all()
    for station in new_stations:
        time_ago = get_time_ago(station.created_at)
        actions.append(RecentAction(
            id=station.id,
            action_type="gas_station_added",
            description=f"Добавлена новая заправка: {station.name}",
            created_at=station.created_at,
            time_ago=time_ago
        ))
    
    # Новые рестораны
    new_restaurants = db.query(Restaurant).order_by(Restaurant.created_at.desc()).limit(limit).all()
    for restaurant in new_restaurants:
        time_ago = get_time_ago(restaurant.created_at)
        actions.append(RecentAction(
            id=restaurant.id,
            action_type="restaurant_added",
            description=f"Добавлен новый ресторан: {restaurant.name}",
            created_at=restaurant.created_at,
            time_ago=time_ago
        ))
    
    # Обновления цен на топливо (из транзакций с типом fuel_price_update)
    fuel_updates = db.query(Transaction).filter(
        Transaction.type == "fuel_price_update"
    ).order_by(Transaction.created_at.desc()).limit(limit).all()
    
    for update in fuel_updates:
        time_ago = get_time_ago(update.created_at)
        actions.append(RecentAction(
            id=update.id,
            action_type="fuel_price_updated",
            description="Обновлены цены на топливо",
            created_at=update.created_at,
            time_ago=time_ago
        ))
    
    # Новые отзывы
    try:
        from app.models.gas_station import Review as GasReview
        new_reviews = db.query(GasReview).order_by(GasReview.created_at.desc()).limit(limit).all()
        for review in new_reviews:
            time_ago = get_time_ago(review.created_at)
            actions.append(RecentAction(
                id=review.id,
                action_type="review_added",
                description=f"Новый отзыв добавлен",
                created_at=review.created_at,
                time_ago=time_ago
            ))
    except Exception:
        pass  # Пропускаем если нет отзывов
    
    # Сортируем по дате и берем последние
    actions.sort(key=lambda x: x.created_at, reverse=True)
    actions = actions[:limit]
    
    total = len(actions)
    
    return RecentActionsResponse(
        actions=actions,
        total=total
    )


def get_time_ago(dt: datetime) -> str:
    """Форматирование времени назад"""
    try:
        from datetime import timezone
        if dt.tzinfo is None:
            # Если нет timezone, считаем что UTC
            now = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            now = datetime.utcnow()
            if now.tzinfo is None and dt.tzinfo is not None:
                # Приводим к одному формату
                dt = dt.replace(tzinfo=None)
        
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} дней назад"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} час{'ов' if hours > 1 else ''} назад"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} минут{'ы' if minutes > 1 else ''} назад"
        else:
            return "только что"
    except Exception:
        return "недавно"


# ==================== Order Statistics ====================

def get_order_statistics(db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> OrderStatisticsResponse:
    """Статистика заказов"""
    start_date, end_date = get_date_range(start_date, end_date)
    
    total_orders = db.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).scalar() or 0
    
    completed = db.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date,
        Transaction.type == "purchase",
        Transaction.amount > 0
    ).scalar() or 0
    
    processing = db.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date,
        Transaction.type.in_(["pending", "processing"])
    ).scalar() or 0
    
    cancelled = db.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date,
        Transaction.type.in_(["cancelled", "refunded"])
    ).scalar() or 0
    
    statuses = []
    if total_orders > 0:
        statuses = [
            OrderStatusStat(
                status="Завершено",
                count=completed,
                percentage=(completed / total_orders) * 100
            ),
            OrderStatusStat(
                status="В обработке",
                count=processing,
                percentage=(processing / total_orders) * 100
            ),
            OrderStatusStat(
                status="Отменено",
                count=cancelled,
                percentage=(cancelled / total_orders) * 100
            )
        ]
    
    return OrderStatisticsResponse(
        total_orders=total_orders,
        statuses=statuses
    )


# ==================== System Activity ====================

def get_system_activity(db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> SystemActivityResponse:
    """Активность системы"""
    start_date, end_date = get_date_range(start_date, end_date)
    previous_start = start_date - (end_date - start_date)
    
    # Общая активность (транзакции)
    total_activity = db.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).scalar() or 0
    
    total_activity_previous = db.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= previous_start,
        Transaction.created_at < start_date
    ).scalar() or 0
    
    # Средний чек
    avg_check = db.query(func.coalesce(func.avg(Transaction.amount), 0)).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date,
        Transaction.amount > 0
    ).scalar() or 0.0
    
    avg_check_previous = db.query(func.coalesce(func.avg(Transaction.amount), 0)).filter(
        Transaction.created_at >= previous_start,
        Transaction.created_at < start_date,
        Transaction.amount > 0
    ).scalar() or 0.0
    
    # Конверсия (процент пользователей, совершивших транзакцию)
    total_users = db.query(func.count(User.id)).scalar() or 1
    users_with_transactions = db.query(func.count(func.distinct(Transaction.user_id))).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).scalar() or 0
    
    conversion = (users_with_transactions / total_users) * 100 if total_users > 0 else 0.0
    
    # Удовлетворенность (средний рейтинг из отзывов)
    from app.models.gas_station import Review as GasReview
    from app.models.restaurant import RestaurantReview
    
    satisfaction = db.query(func.coalesce(func.avg(GasReview.rating), 0)).scalar() or 0.0
    if satisfaction == 0:
        satisfaction = db.query(func.coalesce(func.avg(RestaurantReview.rating), 0)).scalar() or 0.0
    
    return SystemActivityResponse(
        total_activity=KPIValue(
            value=float(total_activity),
            change_percent=calculate_change_percent(total_activity, total_activity_previous),
            change_value=float(total_activity - total_activity_previous)
        ),
        average_check=KPIValue(
            value=float(avg_check),
            change_percent=calculate_change_percent(avg_check, avg_check_previous),
            change_value=float(avg_check - avg_check_previous)
        ),
        conversion=conversion,
        satisfaction=float(satisfaction)
    )

