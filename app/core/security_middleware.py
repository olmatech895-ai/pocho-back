"""
Middleware для дополнительной безопасности
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Добавление заголовков безопасности"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Заголовки безопасности
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Удаляем информацию о сервере
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Ограничение размера запроса"""
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > settings.MAX_REQUEST_SIZE:
                    logger.warning(f"Request too large: {size} bytes from {request.client.host if request.client else 'unknown'}")
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": "Запрос слишком большой"}
                    )
            except ValueError:
                pass
        
        return await call_next(request)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Обработка ошибок с безопасным выводом"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            # HTTP исключения обрабатываем как обычно
            raise
        except Exception as e:
            # Логируем полную ошибку
            logger.error(f"Unhandled exception: {type(e).__name__}: {str(e)}", exc_info=True)
            
            # Возвращаем безопасный ответ
            if settings.HIDE_ERROR_DETAILS:
                detail = "Произошла внутренняя ошибка сервера"
            else:
                detail = f"Ошибка: {str(e)}"
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": detail}
            )

