"""Утилиты доставки: расстояние (haversine), применение тарифа."""
import math

# Радиус Земли в км
EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя точками в км (формула Haversine)."""
    # Валидация входных данных
    if not all(isinstance(x, (int, float)) for x in [lat1, lon1, lat2, lon2]):
        raise ValueError("Координаты должны быть числами")
    
    # Проверка на NaN или Infinity
    if any(math.isnan(x) or math.isinf(x) for x in [lat1, lon1, lat2, lon2]):
        raise ValueError("Координаты не могут быть NaN или Infinity")
    
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    
    # Защита от ошибок округления (a может быть чуть больше 1)
    if a > 1.0:
        a = 1.0
    if a < 0.0:
        a = 0.0
    
    c = 2 * math.asin(math.sqrt(a))
    distance = EARTH_RADIUS_KM * c
    
    # Проверка результата
    if math.isnan(distance) or math.isinf(distance):
        raise ValueError(f"Ошибка расчёта расстояния: получили {distance}")
    
    return distance


def apply_tariff(distance_km: float, cost_per_km: float, min_total: float, base_fixed: float = 0.0) -> float:
    """Итоговая стоимость по тарифу (ТЗ п.3.3): max(расчёт, min_total)."""
    # Валидация входных данных
    if math.isnan(distance_km) or math.isinf(distance_km) or distance_km < 0:
        raise ValueError(f"Некорректное расстояние: {distance_km}")
    if math.isnan(cost_per_km) or math.isinf(cost_per_km) or cost_per_km <= 0:
        raise ValueError(f"Некорректная стоимость за км: {cost_per_km}")
    if math.isnan(min_total) or math.isinf(min_total) or min_total < 0:
        raise ValueError(f"Некорректная минимальная стоимость: {min_total}")
    if math.isnan(base_fixed) or math.isinf(base_fixed) or base_fixed < 0:
        raise ValueError(f"Некорректная базовая стоимость: {base_fixed}")
    
    total = base_fixed + distance_km * cost_per_km
    
    # Проверка результата
    if math.isnan(total) or math.isinf(total):
        raise ValueError(f"Ошибка расчёта стоимости: получили {total}")
    
    return max(total, min_total)
