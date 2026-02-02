"""
API эндпоинты для статистики администратора
"""
from typing import Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_admin_user
from app.schemas.admin_statistics import (
    DashboardResponse,
    KPIsResponse,
    CategoryMetricsResponse,
    RevenueChartResponse,
    NewUsersChartResponse,
    UserActivityChartResponse,
    CategoryDistributionResponse,
    LatestTransactionsResponse,
    CategoryCompletenessResponse,
    RecentActionsResponse,
    OrderStatisticsResponse,
    SystemActivityResponse
)
from app.services.admin_statistics_service.crud import (
    get_kpis,
    get_category_metrics,
    get_revenue_chart,
    get_new_users_chart,
    get_user_activity_chart,
    get_category_distribution,
    get_latest_transactions,
    get_category_completeness,
    get_recent_actions,
    get_order_statistics,
    get_system_activity
)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода"),
    period_days: int = Query(7, ge=1, le=365, description="Количество дней для периода (по умолчанию 7)")
):
    """
    Получение полного дашборда администратора
    
    Возвращает все данные для отображения дашборда:
    - KPI показатели
    - Метрики по категориям
    - Графики (выручка, новые пользователи, активность)
    - Распределение по категориям
    - Последние транзакции
    - Заполненность категорий
    - Последние действия
    - Статистика заказов
    - Активность системы
    """
    try:
        kpis = get_kpis(db, start_date, end_date, period_days)
    except Exception as e:
        import traceback
        print(f"Error getting KPIs: {str(e)}")
        print(traceback.format_exc())
        # Используем значения по умолчанию
        from app.schemas.admin_statistics import KPIValue
        kpis = KPIsResponse(
            total_users=KPIValue(value=0),
            active_users=KPIValue(value=0),
            total_requests=KPIValue(value=0),
            revenue=KPIValue(value=0)
        )
    
    try:
        category_metrics = get_category_metrics(db, start_date, end_date)
    except Exception as e:
        import traceback
        print(f"Error getting category metrics: {str(e)}")
        print(traceback.format_exc())
        from app.schemas.admin_statistics import CategoryMetric
        category_metrics = CategoryMetricsResponse(
            gas_stations=CategoryMetric(total=0, active=0, change=0),
            restaurants=CategoryMetric(total=0, active=0, change=0),
            service_stations=CategoryMetric(total=0, active=0, change=0),
            car_washes=CategoryMetric(total=0, active=0, change=0),
            electric_stations=CategoryMetric(total=0, active=0, change=0)
        )
    
    try:
        revenue_chart = get_revenue_chart(db, start_date, end_date, period_days)
    except Exception as e:
        import traceback
        print(f"Error getting revenue chart: {str(e)}")
        print(traceback.format_exc())
        revenue_chart = RevenueChartResponse(labels=[], revenue=[], orders=[])
    
    try:
        new_users_chart = get_new_users_chart(db, start_date, end_date, period_days)
    except Exception as e:
        import traceback
        print(f"Error getting new users chart: {str(e)}")
        print(traceback.format_exc())
        new_users_chart = NewUsersChartResponse(labels=[], users=[])
    
    try:
        user_activity_chart = get_user_activity_chart(db, start_date, end_date)
    except Exception as e:
        import traceback
        print(f"Error getting user activity chart: {str(e)}")
        print(traceback.format_exc())
        user_activity_chart = UserActivityChartResponse(labels=[], activity=[])
    
    try:
        category_distribution = get_category_distribution(db)
    except Exception as e:
        import traceback
        print(f"Error getting category distribution: {str(e)}")
        print(traceback.format_exc())
        category_distribution = CategoryDistributionResponse(categories=[])
    
    try:
        latest_transactions = get_latest_transactions(db, limit=5)
    except Exception as e:
        import traceback
        print(f"Error getting latest transactions: {str(e)}")
        print(traceback.format_exc())
        latest_transactions = LatestTransactionsResponse(transactions=[], total=0)
    
    try:
        category_completeness = get_category_completeness(db)
    except Exception as e:
        import traceback
        print(f"Error getting category completeness: {str(e)}")
        print(traceback.format_exc())
        category_completeness = CategoryCompletenessResponse(categories=[])
    
    try:
        recent_actions = get_recent_actions(db, limit=5)
    except Exception as e:
        import traceback
        print(f"Error getting recent actions: {str(e)}")
        print(traceback.format_exc())
        recent_actions = RecentActionsResponse(actions=[], total=0)
    
    try:
        order_statistics = get_order_statistics(db, start_date, end_date)
    except Exception as e:
        import traceback
        print(f"Error getting order statistics: {str(e)}")
        print(traceback.format_exc())
        order_statistics = OrderStatisticsResponse(total_orders=0, statuses=[])
    
    try:
        system_activity = get_system_activity(db, start_date, end_date)
    except Exception as e:
        import traceback
        print(f"Error getting system activity: {str(e)}")
        print(traceback.format_exc())
        from app.schemas.admin_statistics import KPIValue
        system_activity = SystemActivityResponse(
            total_activity=KPIValue(value=0),
            average_check=KPIValue(value=0),
            conversion=0.0,
            satisfaction=0.0
        )
    
    return DashboardResponse(
        kpis=kpis,
        category_metrics=category_metrics,
        revenue_chart=revenue_chart,
        new_users_chart=new_users_chart,
        user_activity_chart=user_activity_chart,
        category_distribution=category_distribution,
        latest_transactions=latest_transactions,
        category_completeness=category_completeness,
        recent_actions=recent_actions,
        order_statistics=order_statistics,
        system_activity=system_activity
    )


@router.get("/kpis", response_model=KPIsResponse)
async def get_kpis_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода"),
    period_days: int = Query(7, ge=1, le=365, description="Количество дней для периода")
):
    """Получение основных KPI показателей"""
    return get_kpis(db, start_date, end_date, period_days)


@router.get("/category-metrics", response_model=CategoryMetricsResponse)
async def get_category_metrics_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода")
):
    """Получение метрик по категориям"""
    return get_category_metrics(db, start_date, end_date)


@router.get("/revenue-chart", response_model=RevenueChartResponse)
async def get_revenue_chart_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода"),
    period_days: int = Query(7, ge=1, le=365, description="Количество дней для периода")
):
    """Получение графика выручки"""
    return get_revenue_chart(db, start_date, end_date, period_days)


@router.get("/new-users-chart", response_model=NewUsersChartResponse)
async def get_new_users_chart_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода"),
    period_days: int = Query(7, ge=1, le=365, description="Количество дней для периода")
):
    """Получение графика новых пользователей"""
    return get_new_users_chart(db, start_date, end_date, period_days)


@router.get("/user-activity-chart", response_model=UserActivityChartResponse)
async def get_user_activity_chart_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода")
):
    """Получение графика активности пользователей"""
    return get_user_activity_chart(db, start_date, end_date)


@router.get("/category-distribution", response_model=CategoryDistributionResponse)
async def get_category_distribution_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение распределения по категориям"""
    return get_category_distribution(db)


@router.get("/latest-transactions", response_model=LatestTransactionsResponse)
async def get_latest_transactions_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(5, ge=1, le=100, description="Количество транзакций")
):
    """Получение последних транзакций"""
    return get_latest_transactions(db, limit)


@router.get("/category-completeness", response_model=CategoryCompletenessResponse)
async def get_category_completeness_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Получение заполненности категорий"""
    return get_category_completeness(db)


@router.get("/recent-actions", response_model=RecentActionsResponse)
async def get_recent_actions_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(5, ge=1, le=100, description="Количество действий")
):
    """Получение последних действий"""
    return get_recent_actions(db, limit)


@router.get("/order-statistics", response_model=OrderStatisticsResponse)
async def get_order_statistics_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода")
):
    """Получение статистики заказов"""
    return get_order_statistics(db, start_date, end_date)


@router.get("/system-activity", response_model=SystemActivityResponse)
async def get_system_activity_endpoint(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    start_date: Optional[datetime] = Query(None, description="Начальная дата периода"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата периода")
):
    """Получение активности системы"""
    return get_system_activity(db, start_date, end_date)

