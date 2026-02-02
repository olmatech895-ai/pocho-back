"""
Альтернативный скрипт нагрузочного тестирования с использованием asyncio и aiohttp
Более гибкий контроль над нагрузкой
"""
import asyncio
import aiohttp
import time
import random
import json
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
TARGET_USERS = 20000  # Целевое количество пользователей
CONCURRENT_USERS = 500  # Одновременных пользователей
RAMP_UP_TIME = 300  # Время нарастания нагрузки (секунды)
TEST_DURATION = 600  # Длительность теста (секунды)

# Тестовые данные
TEST_PHONES = [f"+998900000{i:04d}" for i in range(1, TARGET_USERS + 1)]


@dataclass
class TestResult:
    """Результат одного запроса"""
    endpoint: str
    status_code: int
    response_time: float
    success: bool
    error: str = ""


@dataclass
class UserStats:
    """Статистика пользователя"""
    user_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def avg_response_time(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


class LoadTester:
    """Класс для нагрузочного тестирования"""
    
    def __init__(self, base_url: str, api_prefix: str):
        self.base_url = base_url
        self.api_prefix = api_prefix
        self.session: aiohttp.ClientSession = None
        self.results: List[TestResult] = []
        self.user_stats: Dict[str, UserStats] = {}
        self.start_time = None
        self.end_time = None
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            base_url=self.base_url,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def authenticate(self, phone_number: str) -> str:
        """Авторизация пользователя"""
        try:
            # Отправка кода
            async with self.session.post(
                f"{self.api_prefix}/auth/send-code",
                json={"phone_number": phone_number}
            ) as response:
                if response.status != 200:
                    return None
            
            # Верификация кода
            async with self.session.post(
                f"{self.api_prefix}/auth/verify-code",
                json={"phone_number": phone_number, "code": "1234"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "token" in data and "access_token" in data["token"]:
                        return data["token"]["access_token"]
        except Exception as e:
            logger.error(f"Auth error for {phone_number}: {e}")
        return None
    
    async def make_request(
        self,
        method: str,
        endpoint: str,
        user_id: str,
        token: str = None,
        params: Dict = None,
        json_data: Dict = None
    ) -> TestResult:
        """Выполнение HTTP запроса"""
        url = f"{self.api_prefix}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        start_time = time.time()
        try:
            async with self.session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data
            ) as response:
                response_time = (time.time() - start_time) * 1000  # в миллисекундах
                status_code = response.status
                success = 200 <= status_code < 300
                
                result = TestResult(
                    endpoint=endpoint,
                    status_code=status_code,
                    response_time=response_time,
                    success=success,
                    error="" if success else f"HTTP {status_code}"
                )
                
                # Обновление статистики пользователя
                if user_id not in self.user_stats:
                    self.user_stats[user_id] = UserStats(user_id=user_id)
                
                stats = self.user_stats[user_id]
                stats.total_requests += 1
                stats.total_response_time += response_time
                if success:
                    stats.successful_requests += 1
                else:
                    stats.failed_requests += 1
                    stats.errors.append(f"{endpoint}: {status_code}")
                
                self.results.append(result)
                return result
                
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            result = TestResult(
                endpoint=endpoint,
                status_code=0,
                response_time=response_time,
                success=False,
                error="Timeout"
            )
            self.results.append(result)
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = TestResult(
                endpoint=endpoint,
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
            self.results.append(result)
            return result
    
    async def simulate_user(self, user_id: str, phone_number: str):
        """Симуляция поведения одного пользователя"""
        # Авторизация
        token = await self.authenticate(phone_number)
        
        # Список задач пользователя
        tasks = [
            # Заправочные станции
            ("GET", "/gas-stations", {"skip": 0, "limit": 20, "latitude": random.uniform(39.0, 42.0), "longitude": random.uniform(64.0, 68.0), "radius_km": 20}),
            ("GET", "/gas-stations/1", None),
            ("GET", "/gas-stations/search", {"q": "заправка"}),
            
            # Рестораны
            ("GET", "/restaurants", {"skip": 0, "limit": 20, "latitude": random.uniform(39.0, 42.0), "longitude": random.uniform(64.0, 68.0), "radius_km": 20}),
            ("GET", "/restaurants/1", None),
            
            # СТО
            ("GET", "/service-stations", {"skip": 0, "limit": 20, "latitude": random.uniform(39.0, 42.0), "longitude": random.uniform(64.0, 68.0), "radius_km": 20}),
            
            # Автомойки
            ("GET", "/car-washes", {"skip": 0, "limit": 20, "latitude": random.uniform(39.0, 42.0), "longitude": random.uniform(64.0, 68.0), "radius_km": 20}),
            
            # Электрозаправки
            ("GET", "/electric-stations", {"skip": 0, "limit": 20, "latitude": random.uniform(39.0, 42.0), "longitude": random.uniform(64.0, 68.0), "radius_km": 20}),
            
            # Реклама
            ("GET", "/advertisements", {"position": "home"}),
            
            # Профиль
            ("GET", "/profile/me", None),
        ]
        
        # Выполнение задач с паузами
        for method, endpoint, params in tasks:
            await self.make_request(method, endpoint, user_id, token, params)
            await asyncio.sleep(random.uniform(0.5, 2.0))  # Пауза между запросами
    
    async def run_load_test(
        self,
        target_users: int,
        concurrent_users: int,
        ramp_up_time: int,
        test_duration: int
    ):
        """Запуск нагрузочного теста"""
        logger.info("=" * 60)
        logger.info("НАЧАЛО НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
        logger.info("=" * 60)
        logger.info(f"Целевое количество пользователей: {target_users}")
        logger.info(f"Одновременных пользователей: {concurrent_users}")
        logger.info(f"Время нарастания: {ramp_up_time} сек")
        logger.info(f"Длительность теста: {test_duration} сек")
        logger.info("=" * 60)
        
        self.start_time = time.time()
        
        # Создание задач для пользователей
        tasks = []
        users_per_batch = concurrent_users
        batches = (target_users + users_per_batch - 1) // users_per_batch
        
        for batch in range(batches):
            batch_start = batch * users_per_batch
            batch_end = min(batch_start + users_per_batch, target_users)
            
            # Создание задач для текущего батча
            for i in range(batch_start, batch_end):
                phone_number = TEST_PHONES[i]
                user_id = f"user_{i}"
                task = self.simulate_user(user_id, phone_number)
                tasks.append(task)
            
            # Запуск батча с задержкой для нарастания нагрузки
            if batch > 0:
                delay = ramp_up_time / batches
                await asyncio.sleep(delay)
            
            # Запуск батча
            logger.info(f"Запуск батча {batch + 1}/{batches} ({batch_end - batch_start} пользователей)")
            await asyncio.gather(*tasks[batch_start:batch_end], return_exceptions=True)
        
        # Ожидание завершения теста
        await asyncio.sleep(test_duration)
        
        self.end_time = time.time()
        self.print_results()
    
    def print_results(self):
        """Вывод результатов тестирования"""
        duration = self.end_time - self.start_time
        
        total_requests = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total_requests - successful
        
        if total_requests > 0:
            avg_response_time = sum(r.response_time for r in self.results) / total_requests
            max_response_time = max(r.response_time for r in self.results)
            min_response_time = min(r.response_time for r in self.results)
            rps = total_requests / duration if duration > 0 else 0
        else:
            avg_response_time = max_response_time = min_response_time = rps = 0
        
        logger.info("=" * 60)
        logger.info("РЕЗУЛЬТАТЫ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
        logger.info("=" * 60)
        logger.info(f"Длительность теста: {duration:.2f} сек")
        logger.info(f"Всего запросов: {total_requests}")
        logger.info(f"Успешных: {successful} ({successful/total_requests*100:.2f}%)")
        logger.info(f"Неудачных: {failed} ({failed/total_requests*100:.2f}%)")
        logger.info(f"Среднее время ответа: {avg_response_time:.2f} мс")
        logger.info(f"Максимальное время ответа: {max_response_time:.2f} мс")
        logger.info(f"Минимальное время ответа: {min_response_time:.2f} мс")
        logger.info(f"RPS (запросов в секунду): {rps:.2f}")
        logger.info(f"Всего пользователей: {len(self.user_stats)}")
        logger.info("=" * 60)
        
        # Статистика по эндпоинтам
        endpoint_stats = {}
        for result in self.results:
            if result.endpoint not in endpoint_stats:
                endpoint_stats[result.endpoint] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "total_time": 0.0
                }
            stats = endpoint_stats[result.endpoint]
            stats["total"] += 1
            stats["total_time"] += result.response_time
            if result.success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        logger.info("\nСтатистика по эндпоинтам:")
        logger.info("-" * 60)
        for endpoint, stats in sorted(endpoint_stats.items(), key=lambda x: x[1]["total"], reverse=True):
            avg_time = stats["total_time"] / stats["total"] if stats["total"] > 0 else 0
            success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            logger.info(f"{endpoint}:")
            logger.info(f"  Всего: {stats['total']}, Успешных: {stats['success']} ({success_rate:.1f}%), "
                       f"Среднее время: {avg_time:.2f} мс")
        
        # Сохранение результатов в файл
        self.save_results_to_file()
    
    def save_results_to_file(self):
        """Сохранение результатов в файл"""
        filename = f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_data = {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.end_time - self.start_time,
            "total_requests": len(self.results),
            "successful_requests": sum(1 for r in self.results if r.success),
            "failed_requests": sum(1 for r in self.results if not r.success),
            "avg_response_time": sum(r.response_time for r in self.results) / len(self.results) if self.results else 0,
            "results": [
                {
                    "endpoint": r.endpoint,
                    "status_code": r.status_code,
                    "response_time": r.response_time,
                    "success": r.success,
                    "error": r.error
                }
                for r in self.results
            ],
            "user_stats": {
                user_id: {
                    "total_requests": stats.total_requests,
                    "successful_requests": stats.successful_requests,
                    "failed_requests": stats.failed_requests,
                    "avg_response_time": stats.avg_response_time,
                    "success_rate": stats.success_rate
                }
                for user_id, stats in self.user_stats.items()
            }
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nРезультаты сохранены в файл: {filename}")


async def main():
    """Главная функция"""
    async with LoadTester(BASE_URL, API_PREFIX) as tester:
        await tester.run_load_test(
            target_users=TARGET_USERS,
            concurrent_users=CONCURRENT_USERS,
            ramp_up_time=RAMP_UP_TIME,
            test_duration=TEST_DURATION
        )


if __name__ == "__main__":
    asyncio.run(main())






