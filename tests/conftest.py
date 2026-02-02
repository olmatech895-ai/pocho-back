"""
Конфигурация для pytest тестов
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from app.core.config import settings


# Тестовая база данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Создает новую сессию БД для каждого теста"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Создает тестового клиента"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Создает тестового пользователя"""
    user = User(
        phone_number="+998900000001",
        fullname="Test User",
        is_active=True,
        is_admin=False,
        is_blocked=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session):
    """Создает тестового администратора"""
    admin = User(
        phone_number="+998900000002",
        fullname="Test Admin",
        login="admin_test",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_admin=True,
        is_blocked=False
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def user_token(test_user):
    """Создает JWT токен для тестового пользователя"""
    return create_access_token(
        data={
            "sub": {
                "phone_number": test_user.phone_number,
                "id": test_user.id,
            }
        }
    )


@pytest.fixture
def admin_token(test_admin):
    """Создает JWT токен для тестового администратора"""
    return create_access_token(
        data={
            "sub": {
                "phone_number": test_admin.phone_number,
                "id": test_admin.id,
            }
        }
    )

