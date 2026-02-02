"""
Модели для рекламных блоков
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class AdvertisementType(str, enum.Enum):
    """Тип рекламного блока"""
    BANNER = "banner"  # Баннер
    PROMO = "promo"  # Промо-акция
    NOTIFICATION = "notification"  # Уведомление
    POPUP = "popup"  # Всплывающее окно
    CARD = "card"  # Карточка


class AdvertisementStatus(str, enum.Enum):
    """Статус рекламы"""
    ACTIVE = "active"  # Активна
    INACTIVE = "inactive"  # Неактивна
    ARCHIVED = "archived"  # Архивирована


class AdvertisementPosition(str, enum.Enum):
    """Позиция рекламы в приложении"""
    HOME_TOP = "home_top"  # Верх главной страницы
    HOME_BOTTOM = "home_bottom"  # Низ главной страницы
    GAS_STATIONS_LIST = "gas_stations_list"  # В списке заправок
    RESTAURANTS_LIST = "restaurants_list"  # В списке ресторанов
    SERVICE_STATIONS_LIST = "service_stations_list"  # В списке СТО
    CAR_WASHES_LIST = "car_washes_list"  # В списке автомоек
    PROFILE = "profile"  # На странице профиля
    GLOBAL_CHAT = "global_chat"  # В глобальном чате
    OTHER = "other"  # Другое


class Advertisement(Base):
    """Модель рекламного блока"""
    __tablename__ = "advertisements"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    title = Column(String, nullable=False, index=True)  # Заголовок рекламы
    description = Column(Text, nullable=True)  # Описание/текст рекламы
    image_url = Column(String, nullable=False)  # URL изображения рекламы
    
    # Ссылка и действия
    link_url = Column(String, nullable=True)  # URL для перехода при клике
    link_type = Column(String, nullable=True)  # Тип ссылки (internal, external, deep_link)
    
    # Тип и позиция
    ad_type = Column(Enum(AdvertisementType), nullable=False, index=True, default=AdvertisementType.BANNER)
    position = Column(Enum(AdvertisementPosition), nullable=False, index=True, default=AdvertisementPosition.HOME_TOP)
    
    # Статус и видимость
    status = Column(Enum(AdvertisementStatus), nullable=False, index=True, default=AdvertisementStatus.ACTIVE)
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Быстрый фильтр активности
    
    # Временные рамки показа
    start_date = Column(DateTime(timezone=True), nullable=True)  # Дата начала показа
    end_date = Column(DateTime(timezone=True), nullable=True)  # Дата окончания показа
    
    # Приоритет и порядок
    priority = Column(Integer, default=0, nullable=False, index=True)  # Приоритет показа (больше = выше)
    display_order = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Статистика
    views_count = Column(Integer, default=0, nullable=False, index=True)  # Количество просмотров
    clicks_count = Column(Integer, default=0, nullable=False)  # Количество кликов
    
    # Дополнительные параметры
    target_audience = Column(String, nullable=True)  # Целевая аудитория (например, "all", "premium", "new_users")
    show_conditions = Column(Text, nullable=True)  # JSON с условиями показа (например, минимальная версия приложения)
    
    # Кто создал
    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    views = relationship("AdvertisementView", back_populates="advertisement", cascade="all, delete-orphan")
    
    # Индексы
    __table_args__ = (
        Index('idx_advertisement_active_position', 'is_active', 'status', 'position', 'priority'),
        Index('idx_advertisement_dates', 'start_date', 'end_date'),
    )


class AdvertisementView(Base):
    """Модель просмотра рекламы"""
    __tablename__ = "advertisement_views"

    id = Column(Integer, primary_key=True, index=True)
    advertisement_id = Column(Integer, ForeignKey("advertisements.id"), nullable=False, index=True)
    
    # Информация о пользователе
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Если пользователь авторизован
    
    # Техническая информация
    ip_address = Column(String, nullable=True)  # IP адрес
    user_agent = Column(String, nullable=True)  # User-Agent браузера/приложения
    device_type = Column(String, nullable=True)  # Тип устройства (mobile, tablet, desktop)
    app_version = Column(String, nullable=True)  # Версия приложения
    
    # Временная метка
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Связи
    advertisement = relationship("Advertisement", back_populates="views")
    
    # Индексы для аналитики
    __table_args__ = (
        Index('idx_advertisement_view_date', 'advertisement_id', 'viewed_at'),
        Index('idx_advertisement_view_user', 'advertisement_id', 'user_id'),
    )


class AdvertisementClick(Base):
    """Модель клика по рекламе"""
    __tablename__ = "advertisement_clicks"

    id = Column(Integer, primary_key=True, index=True)
    advertisement_id = Column(Integer, ForeignKey("advertisements.id"), nullable=False, index=True)
    
    # Информация о пользователе
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Если пользователь авторизован
    
    # Техническая информация
    ip_address = Column(String, nullable=True)  # IP адрес
    user_agent = Column(String, nullable=True)  # User-Agent браузера/приложения
    device_type = Column(String, nullable=True)  # Тип устройства
    
    # Временная метка
    clicked_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Связи
    advertisement = relationship("Advertisement", foreign_keys=[advertisement_id])
    
    # Индексы для аналитики
    __table_args__ = (
        Index('idx_advertisement_click_date', 'advertisement_id', 'clicked_at'),
        Index('idx_advertisement_click_user', 'advertisement_id', 'user_id'),
    )










