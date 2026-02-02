"""
Тесты для эндпоинтов пользователей
"""
import pytest
from fastapi import status


class TestGetCurrentUser:
    """Тесты для получения текущего пользователя"""
    
    def test_get_me_success(self, client, user_token, test_user):
        """Успешное получение информации о себе"""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["phone_number"] == test_user.phone_number
    
    def test_get_me_unauthorized(self, client):
        """Попытка получить информацию без токена"""
        response = client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_me_invalid_token(self, client):
        """Попытка получить информацию с невалидным токеном"""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetUserById:
    """Тесты для получения пользователя по ID"""
    
    def test_get_user_by_id_success(self, client, user_token, test_user):
        """Успешное получение пользователя по ID"""
        response = client.get(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
    
    def test_get_user_by_id_not_found(self, client, user_token):
        """Получение несуществующего пользователя"""
        response = client.get(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

