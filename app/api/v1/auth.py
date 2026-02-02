from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.core.sms_service import SMSService
from app.core.utils import generate_verification_code, get_code_expiration_time
from app.database import get_db
from app.schemas.user import (
    PhoneNumberRequest,
    VerifyCodeRequest,
    Token,
    CodeSentResponse,
    VerifyCodeResponse,
    UserRegisteredResponse,
    AdminLoginRequest,
    LogoutResponse,
)
from app.crud.user import (
    get_user_by_phone_number,
    get_user_by_login,
    create_user,
    create_verification_code,
    verify_code,
    delete_verification_code,
    add_token_to_blacklist,
)
from app.api.deps import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.core.security import verify_password
from app.messages.auth import SMS_MESSAGE

router = APIRouter()

# Инициализация SMS сервиса
sms_service = SMSService()


@router.post("/send-code", response_model=CodeSentResponse, status_code=status.HTTP_200_OK)
async def send_verification_code(
    request: PhoneNumberRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Отправка SMS кода на номер телефона
    
    - **phone_number**: номер телефона в формате +998XXXXXXXXX
    
    Если пользователь не зарегистрирован, он будет автоматически зарегистрирован после верификации кода.
    """
    try:
        phone_number = request.phone_number
        
        # Генерируем код верификации
        # Для тестового номера используем фиксированный код
        is_test_number = phone_number == settings.SMS_MAIN_PHONE_NUMBER
        if is_test_number:
            verification_code = settings.SMS_MAIN_CODE
            print(f"[SMS] 🧪 ТЕСТОВЫЙ РЕЖИМ: номер {phone_number}, код: {verification_code}")
        else:
            verification_code = generate_verification_code()
            print(f"[SMS] Sending code to {phone_number}, code: {verification_code}")
        
        # Сохраняем код в базе данных
        code_record = create_verification_code(
            db=db,
            phone_number=phone_number,
            code=verification_code
        )
        
        # Отправляем SMS (точно как в примере)
        message = SMS_MESSAGE.format(code=verification_code)
        try:
            sms_service.send_message(
                phone_number=phone_number,
                message=message
            )
        except Exception as sms_error:
            # Логируем ошибку, но не прерываем процесс - код уже сохранен в БД
            print(f"[SMS] Failed to send SMS: {str(sms_error)}")
            # Если это критическая ошибка (не "waiting"), можно решить, что делать
            # Пока просто логируем - код уже сохранен, пользователь может запросить новый
        
        expires_in = settings.SMS_CODE_EXPIRE_MINUTES * 60
        
        return CodeSentResponse(
            message="Код отправлен на ваш номер телефона",
            phone_number=phone_number,
            expires_in=expires_in
        )
        
    except ValueError as e:
        # Ошибка валидации номера телефона
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Обработка всех остальных ошибок
        print(f"Error sending verification code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при отправке кода. Попробуйте позже."
        )


@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_verification_code(
    request: VerifyCodeRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Верификация SMS кода и автоматическая регистрация/авторизация
    
    - **phone_number**: номер телефона в формате +998XXXXXXXXX
    - **code**: 4-значный код из SMS
    
    Если пользователь не зарегистрирован, он будет автоматически зарегистрирован.
    Если зарегистрирован - авторизован и получит JWT токен.
    """
    try:
        phone_number = request.phone_number
        code = request.code
        
        # Обход для тестового номера: код 1111 всегда принимается
        bypass = (
            phone_number == settings.SMS_BYPASS_PHONE and
            code == settings.SMS_BYPASS_CODE
        )
        if bypass:
            verification = True
        else:
            verification = verify_code(
                db=db,
                phone_number=phone_number,
                code=code
            )
        
        if not verification:
            return VerifyCodeResponse(
                is_verified=False,
                message="Неверный код или код истек. Запросите новый код."
            )
        
        # Проверяем, существует ли пользователь
        user = get_user_by_phone_number(db, phone_number)
        
        # Если пользователь не существует - автоматически регистрируем
        if not user:
            user = create_user(db=db, phone_number=phone_number)
        
        # Проверяем, не заблокирован ли пользователь
        if user.is_blocked:
            return VerifyCodeResponse(
                is_verified=False,
                message="Ваш аккаунт заблокирован. Обратитесь к администратору."
            )
        
        # Удаляем использованный код (кроме обхода для тестового номера)
        if not bypass:
            delete_verification_code(db, phone_number)
        
        # Создаем JWT токен
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": {
                    "phone_number": user.phone_number,
                    "id": user.id,
                }
            },
            expires_delta=access_token_expires
        )
        
        token = Token(access_token=access_token, token_type="bearer")
        
        return VerifyCodeResponse(
            is_verified=True,
            message="Код подтвержден успешно" if user else "Регистрация и авторизация прошли успешно",
            token=token
        )
        
    except ValueError as e:
        # Ошибка валидации
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Обработка всех остальных ошибок
        print(f"Error verifying code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при верификации кода. Попробуйте позже."
        )


@router.post("/login", response_model=Token)
async def login(
    request: VerifyCodeRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Авторизация пользователя по коду (альтернативный эндпоинт)
    
    Используйте /verify-code для автоматической регистрации.
    Этот эндпоинт только для авторизации существующих пользователей.
    """
    try:
        phone_number = request.phone_number
        code = request.code
        
        # Обход для тестового номера: код 1111 всегда принимается
        bypass = (
            phone_number == settings.SMS_BYPASS_PHONE and
            code == settings.SMS_BYPASS_CODE
        )
        if bypass:
            verification = True
        else:
            verification = verify_code(db=db, phone_number=phone_number, code=code)
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный код или код истек",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем существование пользователя
        user = get_user_by_phone_number(db, phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден. Используйте /verify-code для регистрации."
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт пользователя деактивирован"
            )
        
        if user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт пользователя заблокирован"
            )
        
        # Удаляем использованный код (кроме обхода для тестового номера)
        if not bypass:
            delete_verification_code(db, phone_number)
        
        # Создаем токен
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": {
                    "phone_number": user.phone_number,
                    "id": user.id,
                }
            },
            expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при авторизации"
        )


@router.post("/check-registration", response_model=UserRegisteredResponse)
async def check_user_registration(
    request: PhoneNumberRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Проверка регистрации пользователя по номеру телефона
    
    - **phone_number**: номер телефона в формате +998XXXXXXXXX
    
    Возвращает:
    - **is_registered**: true если пользователь зарегистрирован, false если нет
    - **phone_number**: проверенный номер телефона
    """
    try:
        phone_number = request.phone_number
        
        # Проверяем наличие пользователя в базе данных
        try:
            user = get_user_by_phone_number(db, phone_number)
            is_registered = user is not None
        except Exception as db_error:
            # Ошибка подключения к базе данных
            print(f"Database error in check_registration: {str(db_error)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка подключения к базе данных: {str(db_error)}"
            )
        
        return UserRegisteredResponse(
            is_registered=is_registered,
            phone_number=phone_number
        )
        
    except HTTPException:
        # Пробрасываем HTTP исключения как есть
        raise
    except ValidationError as e:
        # Ошибка валидации Pydantic - возвращаем детали ошибок
        errors = []
        if hasattr(e, 'errors'):
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error.get("loc", []))
                msg = error.get("msg", "Validation error")
                errors.append(f"{field}: {msg}")
        detail = "; ".join(errors) if errors else str(e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ошибка валидации данных: {detail}"
        )
    except ValueError as e:
        # Ошибка валидации номера телефона
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Обработка всех остальных ошибок
        import traceback
        error_details = traceback.format_exc()
        print(f"Error checking registration: {str(e)}")
        print(f"Traceback: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Произошла ошибка при проверке регистрации: {str(e)}"
        )


@router.post(
    "/admin/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    dependencies=[],
    openapi_extra={
        "security": []
    }
)
async def admin_login(
    request: AdminLoginRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Авторизация администратора по логину и паролю
    
    - **login**: логин администратора
    - **password**: пароль администратора
    
    Возвращает JWT токен для доступа к защищенным эндпоинтам.
    
    ⚠️ Этот эндпоинт не требует токен авторизации - он используется для получения токена.
    """
    try:
        login = request.login
        password = request.password
        
        print(f"[Admin Login] Attempting login for: {login}")
        
        # Получаем пользователя по логину
        user = get_user_by_login(db, login)
        
        if not user:
            print(f"[Admin Login] User not found for login: {login}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"[Admin Login] User found: {user.phone_number}, is_admin: {user.is_admin}, is_active: {user.is_active}, is_blocked: {user.is_blocked}")
        
        # Проверяем, что это администратор
        if not user.is_admin:
            print(f"[Admin Login] User is not admin: {user.phone_number}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        
        # Проверяем, что у пользователя есть пароль (администратор должен иметь пароль)
        if not user.hashed_password:
            print(f"[Admin Login] User has no password: {user.phone_number}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем пароль
        print(f"[Admin Login] Verifying password for user: {user.phone_number}")
        password_valid = verify_password(password, user.hashed_password)
        print(f"[Admin Login] Password valid: {password_valid}")
        
        if not password_valid:
            print(f"[Admin Login] Invalid password for user: {user.phone_number}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем, что пользователь активен
        if not user.is_active:
            print(f"[Admin Login] User is not active: {user.phone_number}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт администратора деактивирован"
            )
        
        # Проверяем, что пользователь не заблокирован
        if user.is_blocked:
            print(f"[Admin Login] User is blocked: {user.phone_number}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Аккаунт администратора заблокирован"
            )
        
        print(f"[Admin Login] Login successful for user: {user.phone_number}")
        
        # Создаем JWT токен
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        # Формируем sub как строку для совместимости с python-jose
        access_token = create_access_token(
            data={
                "sub": f"{user.phone_number}:{user.id}"  # Объединяем в строку
            },
            expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )
    except Exception as e:
        import traceback
        print(f"Error in admin login: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при авторизации администратора"
        )


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def user_logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Выход пользователя из системы
    
    Требует авторизации.
    Добавляет текущий JWT токен в черный список, после чего он не может быть использован.
    """
    try:
        token = credentials.credentials
        
        # Добавляем токен в черный список
        add_token_to_blacklist(db, token, user_id=current_user.id)
        
        return LogoutResponse(
            message="Вы успешно вышли из системы",
            success=True
        )
        
    except Exception as e:
        import traceback
        print(f"Error in user logout: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при выходе из системы"
        )


@router.post("/admin/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def admin_logout(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Выход администратора из системы
    
    Требует прав администратора.
    Добавляет текущий JWT токен в черный список, после чего он не может быть использован.
    """
    try:
        token = credentials.credentials
        
        # Добавляем токен в черный список
        add_token_to_blacklist(db, token, user_id=current_admin.id)
        
        return LogoutResponse(
            message="Вы успешно вышли из системы",
            success=True
        )
        
    except Exception as e:
        import traceback
        print(f"Error in admin logout: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при выходе из системы"
        )
