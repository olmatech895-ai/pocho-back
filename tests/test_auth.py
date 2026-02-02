"""
Тесты для эндпоинтов авторизации
"""
import pytest
from fastapi import status
from app.models.user import User, VerificationCode
from app.core.utils import get_code_expiration_time
from datetime import datetime, timedelta


class TestSendCode:
    """Тесты для отправки SMS кода"""
    
    def test_send_code_success(self, client, db_session):
        """Успешная отправка кода"""
        response = client.post(
            "/api/v1/auth/send-code",
            json={"phone_number": "+998900000100"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "phone_number" in data
        assert data["phone_number"] == "+998900000100"
        assert "expires_in" in data
        
        # Проверяем, что код сохранен в БД
        code = db_session.query(VerificationCode).filter(
            VerificationCode.phone_number == "+998900000100"
        ).first()
        assert code is not None
        assert len(code.code) == 4
    
    def test_send_code_invalid_phone(self, client):
        """Отправка кода на невалидный номер"""
        response = client.post(
            "/api/v1/auth/send-code",
            json={"phone_number": "123456"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_send_code_missing_field(self, client):
        """Отправка запроса без номера телефона"""
        response = client.post(
            "/api/v1/auth/send-code",
            json={}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestVerifyCode:
    """Тесты для верификации кода"""
    
    def test_verify_code_success_new_user(self, client, db_session):
        """Успешная верификация кода для нового пользователя"""
        # Сначала отправляем код
        phone = "+998900000200"
        client.post("/api/v1/auth/send-code", json={"phone_number": phone})
        
        # Получаем код из БД
        code_record = db_session.query(VerificationCode).filter(
            VerificationCode.phone_number == phone
        ).first()
        
        # Верифицируем код
        response = client.post(
            "/api/v1/auth/verify-code",
            json={
                "phone_number": phone,
                "code": code_record.code
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_verified"] is True
        assert "token" in data
        assert "access_token" in data["token"]
        
        # Проверяем, что пользователь создан
        user = db_session.query(User).filter(User.phone_number == phone).first()
        assert user is not None
        assert user.is_active is True
    
    def test_verify_code_invalid_code(self, client, db_session):
        """Верификация с неверным кодом"""
        phone = "+998900000201"
        client.post("/api/v1/auth/send-code", json={"phone_number": phone})
        
        response = client.post(
            "/api/v1/auth/verify-code",
            json={
                "phone_number": phone,
                "code": "9999"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_verified"] is False
    
    def test_verify_code_expired(self, client, db_session):
        """Верификация истекшего кода"""
        phone = "+998900000202"
        # Создаем истекший код
        expired_code = VerificationCode(
            phone_number=phone,
            code="1234",
            expires_at=datetime.utcnow() - timedelta(minutes=10)
        )
        db_session.add(expired_code)
        db_session.commit()
        
        response = client.post(
            "/api/v1/auth/verify-code",
            json={
                "phone_number": phone,
                "code": "1234"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_verified"] is False


class TestCheckRegistration:
    """Тесты для проверки регистрации"""
    
    def test_check_registration_not_registered(self, client):
        """Проверка незарегистрированного пользователя"""
        response = client.post(
            "/api/v1/auth/check-registration",
            json={"phone_number": "+998900000300"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_registered"] is False
    
    def test_check_registration_registered(self, client, test_user):
        """Проверка зарегистрированного пользователя"""
        response = client.post(
            "/api/v1/auth/check-registration",
            json={"phone_number": test_user.phone_number}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_registered"] is True


class TestAdminLogin:
    """Тесты для авторизации администратора"""
    
    def test_admin_login_success(self, client, test_admin):
        """Успешная авторизация администратора"""
        response = client.post(
            "/api/v1/auth/admin/login",
            json={
                "login": test_admin.login,
                "password": "admin123"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_admin_login_invalid_credentials(self, client, test_admin):
        """Авторизация с неверными данными"""
        response = client.post(
            "/api/v1/auth/admin/login",
            json={
                "login": test_admin.login,
                "password": "wrong_password"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_admin_login_not_admin(self, client, test_user):
        """Попытка авторизации не-администратора"""
        # Создаем пользователя с логином, но без прав админа
        response = client.post(
            "/api/v1/auth/admin/login",
            json={
                "login": "user_login",
                "password": "password"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    """Тесты для выхода из системы"""
    
    def test_user_logout_success(self, client, user_token):
        """Успешный выход пользователя"""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Проверяем, что токен больше не работает
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_admin_logout_success(self, client, admin_token):
        """Успешный выход администратора"""
        response = client.post(
            "/api/v1/auth/admin/logout",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

