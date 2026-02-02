from pydantic import BaseModel, field_validator, Field
from datetime import datetime
from typing import Optional, List

from app.core.validators import validate_uzbek_phone_number


class PhoneNumberRequest(BaseModel):
    """Запрос на отправку SMS кода"""
    phone_number: str
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class VerifyCodeRequest(BaseModel):
    """Запрос на верификацию кода"""
    phone_number: str
    code: str
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)
    
    @field_validator('code')
    def validate_code(cls, v: str) -> str:
        """Валидация кода (4 цифры)"""
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Код должен состоять из 4 цифр")
        return v


class Token(BaseModel):
    """JWT токен"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Ответ с информацией о пользователе"""
    id: int
    phone_number: str
    fullname: Optional[str] = None
    is_active: bool
    is_admin: bool = False
    is_blocked: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserDeleteRequest(BaseModel):
    """Запрос на удаление пользователя"""
    phone_number: str
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class UserUpdateAdminRequest(BaseModel):
    """Запрос на изменение статуса администратора"""
    phone_number: str
    is_admin: bool
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class UserUpdateBlockRequest(BaseModel):
    """Запрос на блокировку/разблокировку пользователя"""
    phone_number: str
    is_blocked: bool
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class UserDeleteResponse(BaseModel):
    """Ответ на удаление пользователя"""
    message: str
    phone_number: str
    deleted: bool


class UserUpdateResponse(BaseModel):
    """Ответ на обновление пользователя"""
    message: str
    user: UserResponse


class CodeSentResponse(BaseModel):
    """Ответ об отправке кода"""
    message: str
    phone_number: str
    expires_in: int  # секунды до истечения кода


class VerifyCodeResponse(BaseModel):
    """Ответ на верификацию кода"""
    is_verified: bool
    message: str
    token: Optional[Token] = None


class TokenData(BaseModel):
    """Данные из JWT токена"""
    phone_number: Optional[str] = None
    user_id: Optional[int] = None


class UserRegisteredResponse(BaseModel):
    """Ответ на проверку регистрации пользователя"""
    is_registered: bool
    phone_number: str


class CreateAdminRequest(BaseModel):
    """Запрос на создание администратора"""
    phone_number: str
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class CreateAdminResponse(BaseModel):
    """Ответ на создание администратора"""
    message: str
    phone_number: str
    login: str
    password: str
    user: UserResponse


class AdminLoginRequest(BaseModel):
    """Запрос на авторизацию администратора"""
    login: str
    password: str
    
    @field_validator('login')
    def validate_login(cls, v: str) -> str:
        """Валидация логина"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Логин не может быть пустым")
        return v.strip()
    
    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        """Валидация пароля"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Пароль не может быть пустым")
        return v


class LogoutResponse(BaseModel):
    """Ответ на выход из системы"""
    message: str
    success: bool


class UsersListResponse(BaseModel):
    """Ответ со списком пользователей"""
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


# ==================== Admin User Update Requests ====================

class AdminUpdateUserNameRequest(BaseModel):
    """Запрос администратора на обновление имени пользователя"""
    phone_number: str
    name: str = Field(..., min_length=1, max_length=100, description="Имя пользователя")
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class AdminUpdateUserBalanceRequest(BaseModel):
    """Запрос администратора на обновление баланса пользователя"""
    phone_number: str
    balance: float = Field(..., ge=0, description="Новый баланс пользователя")
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class AdminUpdateUserRatingRequest(BaseModel):
    """Запрос администратора на обновление рейтинга пользователя"""
    phone_number: str
    rating: float = Field(..., ge=0, le=5, description="Рейтинг пользователя (0-5)")
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class AdminUpdateUserLevelRequest(BaseModel):
    """Запрос администратора на обновление уровня пользователя"""
    phone_number: str
    level: str = Field(..., description="Уровень пользователя (например: Новичок, Серебряный, Золотой, Платиновый)")
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class AdminUpdateUserDocumentsRequest(BaseModel):
    """Запрос администратора на обновление документов пользователя"""
    phone_number: str
    passport_verified: Optional[bool] = Field(None, description="Статус верификации паспорта")
    driving_license_verified: Optional[bool] = Field(None, description="Статус верификации водительских прав")
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)


class AdminVerifyDocumentRequest(BaseModel):
    """Запрос администратора на проверку документа пользователя"""
    phone_number: str
    
    @field_validator('phone_number')
    def validate_phone(cls, v: str) -> str:
        """Валидация узбекского номера телефона"""
        return validate_uzbek_phone_number(v)
