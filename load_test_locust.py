"""
Нагрузочное тестирование с использованием Locust
Тестирование на 20000 одновременных пользователей
"""
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import random
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Базовый URL API
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Список тестовых номеров телефонов (для авторизации)
TEST_PHONES = [f"+998900000{i:04d}" for i in range(1, 10001)]  # 10000 номеров


class PochoUser(FastHttpUser):
    """
    Пользователь для нагрузочного тестирования
    """
    wait_time = between(1, 3)  # Пауза между запросами 1-3 секунды
    weight = 10  # Вес пользователя (частота использования)
    
    def on_start(self):
        """Инициализация пользователя - авторизация"""
        self.token = None
        self.phone_number = random.choice(TEST_PHONES)
        self.authenticate()
    
    def authenticate(self):
        """Авторизация пользователя"""
        try:
            # Отправка кода
            response = self.client.post(
                f"{API_PREFIX}/auth/send-code",
                json={"phone_number": self.phone_number},
                name="/auth/send-code"
            )
            
            if response.status_code == 200:
                # Верификация кода (используем тестовый код)
                verify_response = self.client.post(
                    f"{API_PREFIX}/auth/verify-code",
                    json={
                        "phone_number": self.phone_number,
                        "code": "1234"  # Тестовый код
                    },
                    name="/auth/verify-code"
                )
                
                if verify_response.status_code == 200:
                    data = verify_response.json()
                    if "token" in data and "access_token" in data["token"]:
                        self.token = data["token"]["access_token"]
                        logger.info(f"User {self.phone_number} authenticated")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
    
    def get_headers(self):
        """Получение заголовков с токеном"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    # ========== Заправочные станции ==========
    
    @task(10)
    def get_gas_stations(self):
        """Получение списка заправочных станций"""
        params = {
            "skip": 0,
            "limit": 20,
            "latitude": random.uniform(39.0, 42.0),
            "longitude": random.uniform(64.0, 68.0),
            "radius_km": random.randint(5, 50)
        }
        self.client.get(
            f"{API_PREFIX}/gas-stations",
            params=params,
            headers=self.get_headers(),
            name="/gas-stations [list]"
        )
    
    @task(5)
    def get_gas_station_detail(self):
        """Получение детальной информации о заправке"""
        station_id = random.randint(1, 1000)  # Предполагаем до 1000 станций
        self.client.get(
            f"{API_PREFIX}/gas-stations/{station_id}",
            headers=self.get_headers(),
            name="/gas-stations [detail]"
        )
    
    @task(3)
    def search_gas_stations(self):
        """Поиск заправочных станций"""
        search_terms = ["заправка", "бензин", "газ", "АЗС", "нефть"]
        self.client.get(
            f"{API_PREFIX}/gas-stations/search",
            params={"q": random.choice(search_terms)},
            headers=self.get_headers(),
            name="/gas-stations [search]"
        )
    
    @task(2)
    def get_gas_station_photos(self):
        """Получение фотографий заправки"""
        station_id = random.randint(1, 1000)
        self.client.get(
            f"{API_PREFIX}/gas-stations/{station_id}/photos",
            headers=self.get_headers(),
            name="/gas-stations [photos]"
        )
    
    # ========== Рестораны ==========
    
    @task(8)
    def get_restaurants(self):
        """Получение списка ресторанов"""
        params = {
            "skip": 0,
            "limit": 20,
            "latitude": random.uniform(39.0, 42.0),
            "longitude": random.uniform(64.0, 68.0),
            "radius_km": random.randint(5, 50)
        }
        self.client.get(
            f"{API_PREFIX}/restaurants",
            params=params,
            headers=self.get_headers(),
            name="/restaurants [list]"
        )
    
    @task(4)
    def get_restaurant_detail(self):
        """Получение детальной информации о ресторане"""
        restaurant_id = random.randint(1, 500)
        self.client.get(
            f"{API_PREFIX}/restaurants/{restaurant_id}",
            headers=self.get_headers(),
            name="/restaurants [detail]"
        )
    
    @task(2)
    def get_restaurant_menu(self):
        """Получение меню ресторана"""
        restaurant_id = random.randint(1, 500)
        self.client.get(
            f"{API_PREFIX}/restaurants/{restaurant_id}/menu",
            headers=self.get_headers(),
            name="/restaurants [menu]"
        )
    
    # ========== СТО ==========
    
    @task(6)
    def get_service_stations(self):
        """Получение списка СТО"""
        params = {
            "skip": 0,
            "limit": 20,
            "latitude": random.uniform(39.0, 42.0),
            "longitude": random.uniform(64.0, 68.0),
            "radius_km": random.randint(5, 50)
        }
        self.client.get(
            f"{API_PREFIX}/service-stations",
            params=params,
            headers=self.get_headers(),
            name="/service-stations [list]"
        )
    
    @task(3)
    def get_service_station_detail(self):
        """Получение детальной информации о СТО"""
        station_id = random.randint(1, 300)
        self.client.get(
            f"{API_PREFIX}/service-stations/{station_id}",
            headers=self.get_headers(),
            name="/service-stations [detail]"
        )
    
    # ========== Автомойки ==========
    
    @task(5)
    def get_car_washes(self):
        """Получение списка автомоек"""
        params = {
            "skip": 0,
            "limit": 20,
            "latitude": random.uniform(39.0, 42.0),
            "longitude": random.uniform(64.0, 68.0),
            "radius_km": random.randint(5, 50)
        }
        self.client.get(
            f"{API_PREFIX}/car-washes",
            params=params,
            headers=self.get_headers(),
            name="/car-washes [list]"
        )
    
    @task(2)
    def get_car_wash_detail(self):
        """Получение детальной информации об автомойке"""
        wash_id = random.randint(1, 200)
        self.client.get(
            f"{API_PREFIX}/car-washes/{wash_id}",
            headers=self.get_headers(),
            name="/car-washes [detail]"
        )
    
    # ========== Электрозаправки ==========
    
    @task(4)
    def get_electric_stations(self):
        """Получение списка электрозаправок"""
        params = {
            "skip": 0,
            "limit": 20,
            "latitude": random.uniform(39.0, 42.0),
            "longitude": random.uniform(64.0, 68.0),
            "radius_km": random.randint(5, 50)
        }
        self.client.get(
            f"{API_PREFIX}/electric-stations",
            params=params,
            headers=self.get_headers(),
            name="/electric-stations [list]"
        )
    
    @task(2)
    def get_electric_station_detail(self):
        """Получение детальной информации об электрозаправке"""
        station_id = random.randint(1, 100)
        self.client.get(
            f"{API_PREFIX}/electric-stations/{station_id}",
            headers=self.get_headers(),
            name="/electric-stations [detail]"
        )
    
    # ========== Реклама ==========
    
    @task(3)
    def get_advertisements(self):
        """Получение рекламных блоков"""
        positions = ["home", "list", "detail", "cart"]
        self.client.get(
            f"{API_PREFIX}/advertisements",
            params={"position": random.choice(positions)},
            headers=self.get_headers(),
            name="/advertisements [list]"
        )
    
    # ========== Профиль ==========
    
    @task(1)
    def get_profile(self):
        """Получение профиля пользователя"""
        if self.token:
            self.client.get(
                f"{API_PREFIX}/profile/me",
                headers=self.get_headers(),
                name="/profile [me]"
            )
    
    # ========== Уведомления ==========
    
    @task(2)
    def get_notifications(self):
        """Получение уведомлений"""
        if self.token:
            self.client.get(
                f"{API_PREFIX}/notifications",
                params={"skip": 0, "limit": 20},
                headers=self.get_headers(),
                name="/notifications [list]"
            )


# Обработчики событий для статистики
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("=" * 50)
    logger.info("НАЧАЛО НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
    logger.info("=" * 50)
    try:
        if hasattr(environment.runner, 'target_user_count'):
            logger.info(f"Целевое количество пользователей: {environment.runner.target_user_count}")
        # spawn_rate задается при запуске, не доступен через API runner'а
        logger.info("Скорость роста: задается при запуске команды (параметр --spawn-rate)")
    except AttributeError:
        logger.info("Параметры теста будут отображены в веб-интерфейсе")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("=" * 50)
    logger.info("ЗАВЕРШЕНИЕ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
    logger.info("=" * 50)
    
    stats = environment.stats
    total_requests = stats.total.num_requests
    failed_requests = stats.total.num_failures
    successful_requests = total_requests - failed_requests
    logger.info(f"Всего запросов: {total_requests}")
    logger.info(f"Успешных: {successful_requests}")
    logger.info(f"Неудачных: {failed_requests}")
    logger.info(f"Среднее время ответа: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"Максимальное время ответа: {stats.total.max_response_time:.2f}ms")
    logger.info(f"Минимальное время ответа: {stats.total.min_response_time:.2f}ms")
    logger.info(f"RPS (запросов в секунду): {stats.total.total_rps:.2f}")

