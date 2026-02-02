"""
Тесты безопасности
"""
import pytest
from fastapi import status


class TestRateLimiting:
    """Тесты rate limiting"""
    
    def test_rate_limit_auth_endpoint(self, client):
        """Проверка rate limiting для auth эндпоинтов"""
        # Делаем много запросов подряд
        for i in range(10):
            response = client.post(
                "/api/v1/auth/send-code",
                json={"phone_number": f"+998900000{600+i}"}
            )
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                assert "X-RateLimit-Limit" in response.headers
                assert "Retry-After" in response.headers
                break


class TestSecurityHeaders:
    """Тесты заголовков безопасности"""
    
    def test_security_headers_present(self, client):
        """Проверка наличия заголовков безопасности"""
        response = client.get("/")
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers


class TestInputValidation:
    """Тесты валидации входных данных"""
    
    def test_sql_injection_attempt(self, client):
        """Попытка SQL инъекции"""
        # SQLAlchemy защищает от этого, но проверим
        response = client.post(
            "/api/v1/auth/send-code",
            json={"phone_number": "'; DROP TABLE users; --"}
        )
        # Должна быть ошибка валидации, а не SQL ошибка
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
    
    def test_xss_attempt(self, client):
        """Попытка XSS атаки"""
        response = client.post(
            "/api/v1/auth/send-code",
            json={"phone_number": "<script>alert('xss')</script>"}
        )
        # Должна быть ошибка валидации
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestTokenSecurity:
    """Тесты безопасности токенов"""
    
    def test_token_blacklist_after_logout(self, client, user_token):
        """Проверка, что токен не работает после logout"""
        # Сначала используем токен
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Выходим
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Пытаемся использовать токен снова
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_invalid_token_format(self, client):
        """Попытка использовать токен в неправильном формате"""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

