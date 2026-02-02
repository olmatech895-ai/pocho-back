"""
Rate limiting middleware для защиты от DDoS и брутфорса
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette import status
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitStore:
    """In-memory хранилище для rate limiting"""
    def __init__(self):
        self._store: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> Tuple[bool, int]:
        """
        Проверяет, разрешен ли запрос
        Возвращает (разрешено, оставшееся количество запросов)
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Очищаем старые записи
        self._store[key] = [
            timestamp for timestamp in self._store[key]
            if timestamp > window_start
        ]
        
        # Проверяем лимит
        if len(self._store[key]) >= limit:
            remaining = 0
            return False, remaining
        
        # Добавляем текущий запрос
        self._store[key].append(now)
        remaining = limit - len(self._store[key])
        
        return True, remaining
    
    def reset(self, key: str):
        """Сброс счетчика для ключа"""
        if key in self._store:
            del self._store[key]


# Глобальное хранилище
rate_limit_store = RateLimitStore()


def get_client_ip(request: Request) -> str:
    """Получение IP адреса клиента"""
    # Проверяем заголовки прокси
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Берем первый IP из списка
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Используем прямой IP клиента
    if request.client:
        return request.client.host
    
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware для rate limiting"""
    
    async def dispatch(self, request: Request, call_next):
        # Пропускаем rate limiting для документации и статики
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)
        
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        client_ip = get_client_ip(request)
        
        # Определяем лимит в зависимости от эндпоинта
        is_auth_endpoint = request.url.path.startswith(f"{settings.API_V1_PREFIX}/auth")
        limit = settings.RATE_LIMIT_AUTH_PER_MINUTE if is_auth_endpoint else settings.RATE_LIMIT_PER_MINUTE
        
        # Проверяем rate limit
        allowed, remaining = rate_limit_store.is_allowed(
            key=f"{client_ip}:{request.url.path}",
            limit=limit,
            window_seconds=60
        )
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}, path: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Превышен лимит запросов. Попробуйте позже.",
                    "retry_after": 60
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60"
                }
            )
        
        # Добавляем заголовки с информацией о rate limit
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response

