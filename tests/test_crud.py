"""
Тесты для CRUD операций
"""
import pytest
from app.crud.user import (
    get_user_by_phone_number,
    create_user,
    delete_user,
    set_admin_status,
    set_block_status,
    is_token_blacklisted,
    add_token_to_blacklist,
)
from app.models.user import User, BlacklistedToken


class TestUserCRUD:
    """Тесты CRUD операций с пользователями"""
    
    def test_create_user(self, db_session):
        """Создание пользователя"""
        user = create_user(db_session, "+998900000700")
        assert user is not None
        assert user.phone_number == "+998900000700"
        assert user.is_active is True
        assert user.is_admin is False
    
    def test_get_user_by_phone(self, db_session):
        """Получение пользователя по номеру телефона"""
        user = create_user(db_session, "+998900000701")
        found_user = get_user_by_phone_number(db_session, "+998900000701")
        assert found_user is not None
        assert found_user.id == user.id
    
    def test_delete_user(self, db_session):
        """Удаление пользователя"""
        user = create_user(db_session, "+998900000702")
        deleted = delete_user(db_session, "+998900000702")
        assert deleted is True
        
        found_user = get_user_by_phone_number(db_session, "+998900000702")
        assert found_user is None
    
    def test_set_admin_status(self, db_session):
        """Назначение администратора"""
        user = create_user(db_session, "+998900000703")
        updated_user = set_admin_status(db_session, "+998900000703", True)
        assert updated_user.is_admin is True
    
    def test_set_block_status(self, db_session):
        """Блокировка пользователя"""
        user = create_user(db_session, "+998900000704")
        updated_user = set_block_status(db_session, "+998900000704", True)
        assert updated_user.is_blocked is True
        assert updated_user.is_active is False  # Блокированный деактивирован


class TestTokenBlacklist:
    """Тесты черного списка токенов"""
    
    def test_add_token_to_blacklist(self, db_session):
        """Добавление токена в черный список"""
        token = "test_token_123"
        blacklisted = add_token_to_blacklist(db_session, token, user_id=1)
        assert blacklisted is not None
        assert blacklisted.token == token
    
    def test_is_token_blacklisted(self, db_session):
        """Проверка токена в черном списке"""
        token = "test_token_456"
        assert is_token_blacklisted(db_session, token) is False
        
        add_token_to_blacklist(db_session, token)
        assert is_token_blacklisted(db_session, token) is True

