from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from jose.exceptions import JWTClaimsError, ExpiredSignatureError

from app.core.config import settings
from app.database import get_db
from app.models.user import User
from app.crud.user import get_user_by_phone_number, get_user_by_id, is_token_blacklisted, has_any_admin

# Используем HTTPBearer вместо OAuth2PasswordBearer для JWT токенов
security = HTTPBearer()
# Опциональный security для случаев, когда токен может отсутствовать
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """
    Получение текущего пользователя из JWT токена
    Защита от невалидных токенов и ошибок декодирования
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please check your token and try again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        
        # Проверяем, не находится ли токен в черном списке
        if is_token_blacklisted(db, token):
            print("Authentication error: Token is blacklisted")
            raise credentials_exception
        
        try:
            # Декодируем токен с отключенной проверкой sub (так как мы используем словарь)
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_sub": False}  # Отключаем проверку sub, так как используем словарь
            )
        except ExpiredSignatureError:
            print("Authentication error: Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTClaimsError as e:
            print(f"Authentication error: JWT claims error - {str(e)}")
            raise credentials_exception
        except JWTError as e:
            print(f"Authentication error: JWT error - {str(e)}")
            raise credentials_exception
        
        # Получаем данные из токена
        # Форматы sub:
        # 1. Новый формат: "{phone_number}:{id}" (например, "+998900174777:7")
        # 2. Старый формат: словарь с phone_number и id
        # 3. Очень старый формат: просто phone_number (строка)
        sub = payload.get("sub")
        user_id = payload.get("user_id")  # Может быть в отдельном поле
        
        phone_number = None
        
        # Поддерживаем разные форматы для обратной совместимости
        if isinstance(sub, dict):
            # Старый формат: sub - словарь
            phone_number = sub.get("phone_number")
            if not user_id:
                user_id = sub.get("id")
        elif isinstance(sub, str):
            # Новый формат: sub - строка, может быть "{phone_number}:{id}" или просто phone_number
            if ":" in sub:
                # Формат "{phone_number}:{id}"
                parts = sub.split(":", 1)
                phone_number = parts[0] if len(parts) > 0 else None
                if not user_id and len(parts) > 1:
                    try:
                        user_id = int(parts[1])
                    except (ValueError, IndexError):
                        pass
            else:
                # Просто phone_number
                phone_number = sub
        
        if not phone_number and not user_id:
            print("Authentication error: No phone_number or user_id in token")
            raise credentials_exception
        
        # Получаем пользователя по user_id (предпочтительно) или phone_number
        user = None
        if user_id:
            user = get_user_by_id(db, user_id)
            if not user:
                print(f"Authentication error: User with id {user_id} not found")
        elif phone_number:
            user = get_user_by_phone_number(db, phone_number)
            if not user:
                print(f"Authentication error: User with phone_number {phone_number} not found")
        
        if user is None:
            raise credentials_exception
        
        return user
        
    except HTTPException:
        # Пробрасываем HTTP исключения как есть
        raise
    except JWTError as e:
        print(f"Authentication error: JWT error - {str(e)}")
        raise credentials_exception
    except Exception as e:
        # Логируем ошибку для отладки
        import traceback
        print(f"Authentication error: {type(e).__name__}: {str(e)}")
        print(traceback.format_exc())
        raise credentials_exception


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Получение активного пользователя
    Проверка статуса активности и блокировки пользователя
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    if current_user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked"
        )
    
    return current_user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Получение текущего администратора
    Проверка прав администратора
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin rights required."
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[Annotated[HTTPAuthorizationCredentials, Depends(optional_security)]] = None,
    db: Annotated[Session, Depends(get_db)] = None
) -> Optional[User]:
    """
    Опциональное получение текущего пользователя из JWT токена
    Если токен отсутствует или невалиден - возвращает None
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        
        # Проверяем, не находится ли токен в черном списке
        if is_token_blacklisted(db, token):
            return None
        
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_sub": False}
            )
        except (JWTError, ExpiredSignatureError, JWTClaimsError):
            return None
        
        # Получаем данные из токена
        sub = payload.get("sub")
        user_id = payload.get("user_id")
        
        phone_number = None
        
        if isinstance(sub, dict):
            phone_number = sub.get("phone_number")
            if not user_id:
                user_id = sub.get("id")
        elif isinstance(sub, str):
            if ":" in sub:
                parts = sub.split(":", 1)
                phone_number = parts[0] if len(parts) > 0 else None
                if not user_id and len(parts) > 1:
                    try:
                        user_id = int(parts[1])
                    except (ValueError, IndexError):
                        pass
            else:
                phone_number = sub
        
        if not phone_number and not user_id:
            return None
        
        # Получаем пользователя
        user = None
        if user_id:
            user = get_user_by_id(db, user_id)
        elif phone_number:
            user = get_user_by_phone_number(db, phone_number)
        
        if user and not user.is_active:
            return None
        
        if user and user.is_blocked:
            return None
        
        return user
        
    except Exception:
        return None


async def get_optional_admin_user_for_create(
    db: Annotated[Session, Depends(get_db)],
    credentials: Optional[Annotated[HTTPAuthorizationCredentials, Depends(optional_security)]] = None
) -> Optional[User]:
    """
    Условное получение текущего администратора для создания первого админа
    Если в базе нет админов - возвращает None (разрешает создание без токена)
    Если в базе есть админы - требует токен и возвращает админа
    """
    # Проверяем наличие админов в базе
    if has_any_admin(db):
        # Если админы есть - токен обязателен
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Admin token is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем токен и возвращаем админа
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            token = credentials.credentials
            
            # Проверяем, не находится ли токен в черном списке
            if is_token_blacklisted(db, token):
                raise credentials_exception
            
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            # Получаем данные из токена
            sub = payload.get("sub")
            user_id = payload.get("user_id")
            
            phone_number = None
            
            # Поддерживаем разные форматы для обратной совместимости
            if isinstance(sub, dict):
                # Старый формат: sub - словарь
                phone_number = sub.get("phone_number")
                if not user_id:
                    user_id = sub.get("id")
            elif isinstance(sub, str):
                # Новый формат: sub - строка, может быть "{phone_number}:{id}" или просто phone_number
                if ":" in sub:
                    # Формат "{phone_number}:{id}"
                    parts = sub.split(":", 1)
                    phone_number = parts[0] if len(parts) > 0 else None
                    if not user_id and len(parts) > 1:
                        try:
                            user_id = int(parts[1])
                        except (ValueError, IndexError):
                            pass
                else:
                    # Просто phone_number
                    phone_number = sub
            
            if not phone_number and not user_id:
                raise credentials_exception
            
            # Получаем пользователя по user_id (предпочтительно) или phone_number
            user = None
            if user_id:
                user = get_user_by_id(db, user_id)
            elif phone_number:
                user = get_user_by_phone_number(db, phone_number)
            
            if user is None:
                raise credentials_exception
            
            # Проверяем, что это админ
            if not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Admin rights required."
                )
            
            # Проверяем активность и блокировку
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive"
                )
            
            if user.is_blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is blocked"
                )
            
            return user
            
        except JWTError:
            raise credentials_exception
        except HTTPException:
            raise
        except Exception as e:
            print(f"Authentication error: {str(e)[:50]}")
            raise credentials_exception
    else:
        # Если админов нет - разрешаем создание без токена
        return None
