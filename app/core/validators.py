import re
from typing import Optional
from pydantic import field_validator, ValidationError


def validate_uzbek_phone_number(phone: str) -> str:
    """
    Валидация узбекского номера телефона
    Формат: +998XXXXXXXXX (9 цифр после +998)
    Пример: +998900000000
    """
    if not isinstance(phone, str):
        raise ValueError("Номер телефона должен быть строкой")
    
    # Удаляем все пробелы и дефисы
    phone = phone.strip().replace(" ", "").replace("-", "")
    
    # Проверяем, что номер не пустой
    if not phone:
        raise ValueError("Номер телефона не может быть пустым")
    
    # Проверяем формат +998XXXXXXXXX (9 цифр после +998)
    pattern = r'^\+998\d{9}$'
    
    if not re.match(pattern, phone):
        raise ValueError(
            f"Неверный формат номера телефона: '{phone}'. "
            "Используйте формат: +998XXXXXXXXX (например: +998900000000). "
            "После +998 должно быть ровно 9 цифр."
        )
    
    return phone


class PhoneNumberValidator:
    """Валидатор для узбекских номеров телефона"""
    
    @staticmethod
    @field_validator('phone_number', mode='before')
    def validate_phone(cls, v: str) -> str:
        """Валидация номера телефона"""
        if isinstance(v, str):
            return validate_uzbek_phone_number(v)
        raise ValueError("Номер телефона должен быть строкой")




