"""
Схемы для статистики администратора
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== KPIs ====================

class KPIValue(BaseModel):
    """Значение KPI с трендом"""
    value: float
    change_percent: Optional[float] = None
    change_value: Optional[float] = None
    period_value: Optional[float] = None  # Значение за период (например, за месяц)

    class Config:
        from_attributes = True


class KPIsResponse(BaseModel):
    """Основные KPI показатели"""
    total_users: KPIValue
    active_users: KPIValue
    total_requests: KPIValue
    revenue: KPIValue

    class Config:
        from_attributes = True


# ==================== Category Metrics ====================

class CategoryMetric(BaseModel):
    """Метрика по категории"""
    total: int
    active: int
    change: int  # Изменение за период

    class Config:
        from_attributes = True


class CategoryMetricsResponse(BaseModel):
    """Метрики по категориям"""
    gas_stations: CategoryMetric
    restaurants: CategoryMetric
    service_stations: CategoryMetric
    car_washes: CategoryMetric
    electric_stations: CategoryMetric

    class Config:
        from_attributes = True


# ==================== Charts ====================

class ChartDataPoint(BaseModel):
    """Точка данных для графика"""
    label: str  # Метка (например, "1ч", "2ч", или дата)
    value: float

    class Config:
        from_attributes = True


class RevenueChartResponse(BaseModel):
    """График выручки"""
    labels: List[str]
    revenue: List[float]  # Сумма
    orders: List[int]  # Количество заказов

    class Config:
        from_attributes = True


class NewUsersChartResponse(BaseModel):
    """График новых пользователей"""
    labels: List[str]
    users: List[int]

    class Config:
        from_attributes = True


class UserActivityChartResponse(BaseModel):
    """График активности пользователей"""
    labels: List[str]  # Временные метки
    activity: List[int]  # Уровень активности

    class Config:
        from_attributes = True


class CategoryDistributionItem(BaseModel):
    """Элемент распределения по категориям"""
    category: str
    count: int
    percentage: float
    color: Optional[str] = None  # Цвет для отображения

    class Config:
        from_attributes = True


class CategoryDistributionResponse(BaseModel):
    """Распределение по категориям (круговая диаграмма)"""
    categories: List[CategoryDistributionItem]

    class Config:
        from_attributes = True


# ==================== Transactions ====================

class TransactionListItem(BaseModel):
    """Элемент списка транзакций"""
    id: int
    user_name: str
    user_phone: str
    type: str  # Тип категории (Заправки, Рестораны, и т.д.)
    amount: float
    status: str  # Завершено, В обработке, Отменено
    created_at: datetime

    class Config:
        from_attributes = True


class LatestTransactionsResponse(BaseModel):
    """Последние транзакции"""
    transactions: List[TransactionListItem]
    total: int

    class Config:
        from_attributes = True


# ==================== Category Completeness ====================

class CategoryCompletenessItem(BaseModel):
    """Заполненность категории"""
    category: str
    current: int
    target: int
    percentage: float

    class Config:
        from_attributes = True


class CategoryCompletenessResponse(BaseModel):
    """Заполненность категорий"""
    categories: List[CategoryCompletenessItem]

    class Config:
        from_attributes = True


# ==================== Recent Actions ====================

class RecentAction(BaseModel):
    """Последнее действие"""
    id: int
    action_type: str  # Тип действия
    description: str
    created_at: datetime
    time_ago: str  # Время назад (например, "2 минуты назад")

    class Config:
        from_attributes = True


class RecentActionsResponse(BaseModel):
    """Последние действия"""
    actions: List[RecentAction]
    total: int

    class Config:
        from_attributes = True


# ==================== Order Statistics ====================

class OrderStatusStat(BaseModel):
    """Статистика по статусу заказа"""
    status: str
    count: int
    percentage: float

    class Config:
        from_attributes = True


class OrderStatisticsResponse(BaseModel):
    """Статистика заказов"""
    total_orders: int
    statuses: List[OrderStatusStat]

    class Config:
        from_attributes = True


# ==================== System Activity ====================

class SystemActivityResponse(BaseModel):
    """Активность системы"""
    total_activity: KPIValue
    average_check: KPIValue
    conversion: float  # Конверсия в процентах
    satisfaction: float  # Удовлетворенность (0-5)

    class Config:
        from_attributes = True


# ==================== Dashboard Response ====================

class DashboardResponse(BaseModel):
    """Полный ответ дашборда"""
    kpis: KPIsResponse
    category_metrics: CategoryMetricsResponse
    revenue_chart: RevenueChartResponse
    new_users_chart: NewUsersChartResponse
    user_activity_chart: UserActivityChartResponse
    category_distribution: CategoryDistributionResponse
    latest_transactions: LatestTransactionsResponse
    category_completeness: CategoryCompletenessResponse
    recent_actions: RecentActionsResponse
    order_statistics: OrderStatisticsResponse
    system_activity: SystemActivityResponse

    class Config:
        from_attributes = True


# ==================== Date Range Filter ====================

class DateRangeFilter(BaseModel):
    """Фильтр по датам"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period_days: Optional[int] = Field(7, description="Количество дней для периода (по умолчанию 7)")

    class Config:
        from_attributes = True










