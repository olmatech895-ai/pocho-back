"""
Конфигурация для нагрузочного тестирования
"""
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class LoadTestConfig:
    """Конфигурация нагрузочного теста"""
    # Базовые настройки
    base_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"
    
    # Параметры нагрузки
    target_users: int = 20000  # Целевое количество пользователей
    concurrent_users: int = 500  # Одновременных пользователей
    ramp_up_time: int = 300  # Время нарастания нагрузки (секунды)
    test_duration: int = 600  # Длительность теста (секунды)
    
    # Настройки запросов
    request_timeout: int = 30  # Таймаут запроса (секунды)
    connection_timeout: int = 10  # Таймаут подключения (секунды)
    
    # Паузы между запросами
    min_wait_time: float = 0.5  # Минимальная пауза (секунды)
    max_wait_time: float = 2.0  # Максимальная пауза (секунды)
    
    # Тестовые данные
    test_phone_prefix: str = "+998900000"
    test_code: str = "1234"
    
    # Эндпоинты для тестирования
    endpoints: List[Dict] = None
    
    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = [
                # Заправочные станции
                {
                    "method": "GET",
                    "endpoint": "/gas-stations",
                    "weight": 10,
                    "params": {
                        "skip": 0,
                        "limit": 20,
                        "latitude": (39.0, 42.0),  # Диапазон
                        "longitude": (64.0, 68.0),
                        "radius_km": (5, 50)
                    }
                },
                {
                    "method": "GET",
                    "endpoint": "/gas-stations/{id}",
                    "weight": 5,
                    "params": None,
                    "id_range": (1, 1000)
                },
                {
                    "method": "GET",
                    "endpoint": "/gas-stations/search",
                    "weight": 3,
                    "params": {
                        "q": ["заправка", "бензин", "газ", "АЗС"]
                    }
                },
                {
                    "method": "GET",
                    "endpoint": "/gas-stations/{id}/photos",
                    "weight": 2,
                    "params": None,
                    "id_range": (1, 1000)
                },
                
                # Рестораны
                {
                    "method": "GET",
                    "endpoint": "/restaurants",
                    "weight": 8,
                    "params": {
                        "skip": 0,
                        "limit": 20,
                        "latitude": (39.0, 42.0),
                        "longitude": (64.0, 68.0),
                        "radius_km": (5, 50)
                    }
                },
                {
                    "method": "GET",
                    "endpoint": "/restaurants/{id}",
                    "weight": 4,
                    "params": None,
                    "id_range": (1, 500)
                },
                {
                    "method": "GET",
                    "endpoint": "/restaurants/{id}/menu",
                    "weight": 2,
                    "params": None,
                    "id_range": (1, 500)
                },
                
                # СТО
                {
                    "method": "GET",
                    "endpoint": "/service-stations",
                    "weight": 6,
                    "params": {
                        "skip": 0,
                        "limit": 20,
                        "latitude": (39.0, 42.0),
                        "longitude": (64.0, 68.0),
                        "radius_km": (5, 50)
                    }
                },
                {
                    "method": "GET",
                    "endpoint": "/service-stations/{id}",
                    "weight": 3,
                    "params": None,
                    "id_range": (1, 300)
                },
                
                # Автомойки
                {
                    "method": "GET",
                    "endpoint": "/car-washes",
                    "weight": 5,
                    "params": {
                        "skip": 0,
                        "limit": 20,
                        "latitude": (39.0, 42.0),
                        "longitude": (64.0, 68.0),
                        "radius_km": (5, 50)
                    }
                },
                {
                    "method": "GET",
                    "endpoint": "/car-washes/{id}",
                    "weight": 2,
                    "params": None,
                    "id_range": (1, 200)
                },
                
                # Электрозаправки
                {
                    "method": "GET",
                    "endpoint": "/electric-stations",
                    "weight": 4,
                    "params": {
                        "skip": 0,
                        "limit": 20,
                        "latitude": (39.0, 42.0),
                        "longitude": (64.0, 68.0),
                        "radius_km": (5, 50)
                    }
                },
                {
                    "method": "GET",
                    "endpoint": "/electric-stations/{id}",
                    "weight": 2,
                    "params": None,
                    "id_range": (1, 100)
                },
                
                # Реклама
                {
                    "method": "GET",
                    "endpoint": "/advertisements",
                    "weight": 3,
                    "params": {
                        "position": ["home", "list", "detail", "cart"]
                    }
                },
                
                # Профиль
                {
                    "method": "GET",
                    "endpoint": "/profile/me",
                    "weight": 1,
                    "params": None,
                    "requires_auth": True
                },
                
                # Уведомления
                {
                    "method": "GET",
                    "endpoint": "/notifications",
                    "weight": 2,
                    "params": {
                        "skip": 0,
                        "limit": 20
                    },
                    "requires_auth": True
                },
            ]


# Глобальная конфигурация
config = LoadTestConfig()






