from fastapi import APIRouter

from app.api.v1 import (
    auth,
    # users,  # Отключено
    admin,
    admin_statistics,
    # user_extended,  # Отключено
    favorites,
    profile,
    # achievements,  # Отключено - будет переделано
    notifications,
    support,
    global_chat,
    gas_stations,
    admin_gas_stations,
    restaurants,
    admin_restaurants,
    service_stations,
    admin_service_stations,
    car_washes,
    admin_car_washes,
    advertisements,
    admin_advertisements,
    electric_stations,
    admin_electric_stations,
    drivers,
    admin_drivers,
    regions,
    delivery,
    delivery_driver,
    admin_delivery,
    # transactions,  # Отключено
    # statistics,  # Отключено
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Авторизация"])
# api_router.include_router(users.router, prefix="/users", tags=["Пользователи"])  # Отключено
api_router.include_router(admin.router, prefix="/admin", tags=["Администрирование"])
api_router.include_router(admin_statistics.router, prefix="/admin/statistics", tags=["Админ: Статистика"])

# Расширенные эндпоинты пользователя
# api_router.include_router(user_extended.router, prefix="/user", tags=["Пользователь (расширенный)"])  # Отключено
api_router.include_router(profile.router, prefix="/profile", tags=["Профиль"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["Избранное"])
# api_router.include_router(achievements.router, prefix="/achievements", tags=["Достижения"])  # Отключено - будет переделано
api_router.include_router(notifications.router, prefix="/notifications", tags=["Уведомления"])
api_router.include_router(support.router, prefix="/support", tags=["Техническая поддержка"])
api_router.include_router(global_chat.router, prefix="/global-chat", tags=["Глобальный чат"])
api_router.include_router(gas_stations.router, prefix="/gas-stations", tags=["Заправочные станции"])
api_router.include_router(admin_gas_stations.router, prefix="/admin/gas-stations", tags=["Админ: Заправочные станции"])
api_router.include_router(restaurants.router, prefix="/restaurants", tags=["Рестораны"])
api_router.include_router(admin_restaurants.router, prefix="/admin/restaurants", tags=["Админ: Рестораны"])
api_router.include_router(service_stations.router, prefix="/service-stations", tags=["СТО"])
api_router.include_router(admin_service_stations.router, prefix="/admin/service-stations", tags=["Админ: СТО"])
api_router.include_router(car_washes.router, prefix="/car-washes", tags=["Автомойки"])
api_router.include_router(admin_car_washes.router, prefix="/admin/car-washes", tags=["Админ: Автомойки"])
api_router.include_router(advertisements.router, prefix="/advertisements", tags=["Реклама"])
api_router.include_router(admin_advertisements.router, prefix="/admin/advertisements", tags=["Админ: Реклама"])
api_router.include_router(electric_stations.router, prefix="/electric-stations", tags=["Электрозаправки"])
api_router.include_router(admin_electric_stations.router, prefix="/admin/electric-stations", tags=["Админ: Электрозаправки"])
api_router.include_router(drivers.router, tags=["Водители"])
api_router.include_router(admin_drivers.router, tags=["Админ: Водители"])
api_router.include_router(regions.router, tags=["Регионы"])
api_router.include_router(delivery.router, tags=["Доставка"])
api_router.include_router(delivery_driver.router, tags=["Доставка: Водитель"])
api_router.include_router(admin_delivery.router, tags=["Админ: Доставка"])
# api_router.include_router(transactions.router, prefix="/transactions", tags=["Транзакции"])  # Отключено
# api_router.include_router(statistics.router, prefix="/statistics", tags=["Статистика"])  # Отключено




