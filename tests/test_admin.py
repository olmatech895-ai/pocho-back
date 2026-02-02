"""
Тесты для эндпоинтов администратора
"""
import pytest
from fastapi import status
from app.models.user import User


class TestCreateAdmin:
    """Тесты для создания администратора"""
    
    def test_create_admin_success(self, client, admin_token):
        """Успешное создание администратора"""
        response = client.post(
            "/api/v1/admin/create-admin",
            json={"phone_number": "+998900000400"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "login" in data
        assert "password" in data
        assert "user" in data
        assert data["user"]["is_admin"] is True
        assert len(data["login"]) > 0
        assert len(data["password"]) > 0
    
    def test_create_admin_unauthorized(self, client):
        """Попытка создать администратора без токена"""
        response = client.post(
            "/api/v1/admin/create-admin",
            json={"phone_number": "+998900000401"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_create_admin_not_admin(self, client, user_token):
        """Попытка создать администратора обычным пользователем"""
        response = client.post(
            "/api/v1/admin/create-admin",
            json={"phone_number": "+998900000402"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_create_admin_existing_user(self, client, admin_token, test_user):
        """Попытка создать администратора из существующего пользователя"""
        response = client.post(
            "/api/v1/admin/create-admin",
            json={"phone_number": test_user.phone_number},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDeleteUser:
    """Тесты для удаления пользователя"""
    
    def test_delete_user_success(self, client, admin_token, db_session):
        """Успешное удаление пользователя"""
        # Создаем пользователя для удаления
        user = User(
            phone_number="+998900000500",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        user_id = user.id
        
        response = client.delete(
            f"/api/v1/admin/user",
            json={"phone_number": "+998900000500"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Проверяем, что пользователь удален
        deleted_user = db_session.query(User).filter(User.id == user_id).first()
        assert deleted_user is None
    
    def test_delete_user_not_found(self, client, admin_token):
        """Удаление несуществующего пользователя"""
        response = client.delete(
            "/api/v1/admin/user",
            json={"phone_number": "+998999999999"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSetAdminStatus:
    """Тесты для назначения администратора"""
    
    def test_set_admin_status_success(self, client, admin_token, test_user):
        """Успешное назначение администратора"""
        response = client.post(
            "/api/v1/admin/user/admin",
            json={
                "phone_number": test_user.phone_number,
                "is_admin": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user"]["is_admin"] is True


class TestBlockUser:
    """Тесты для блокировки пользователя"""
    
    def test_block_user_success(self, client, admin_token, test_user):
        """Успешная блокировка пользователя"""
        response = client.post(
            "/api/v1/admin/user/block",
            json={
                "phone_number": test_user.phone_number,
                "is_blocked": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user"]["is_blocked"] is True
        assert data["user"]["is_active"] is False  # Блокированный пользователь деактивирован

