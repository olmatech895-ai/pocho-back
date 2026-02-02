"""
Модели для ресторанов
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class CuisineType(str, enum.Enum):
    """Типы кухни"""
    UZBEK = "Узбекская"
    RUSSIAN = "Русская"
    EUROPEAN = "Европейская"
    ASIAN = "Азиатская"
    ITALIAN = "Итальянская"
    JAPANESE = "Японская"
    CHINESE = "Китайская"
    AMERICAN = "Американская"
    FAST_FOOD = "Фастфуд"
    PIZZA = "Пицца"
    SUSHI = "Суши"
    GRILL = "Гриль"
    VEGETARIAN = "Вегетарианская"
    OTHER = "Другая"


class RestaurantStatus(str, enum.Enum):
    """Статус ресторана"""
    PENDING = "pending"  # Ожидает модерации
    APPROVED = "approved"  # Одобрен
    REJECTED = "rejected"  # Отклонен
    ARCHIVED = "archived"  # Архивирован


class Restaurant(Base):
    """Модель ресторана"""
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    name = Column(String, nullable=False, index=True)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)  # Широта
    longitude = Column(Float, nullable=False)  # Долгота
    
    # Контактная информация
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    # Режим работы
    is_24_7 = Column(Boolean, default=False, nullable=False)  # Работает 24/7
    working_hours = Column(String, nullable=True)  # Например: "09:00-23:00"
    
    # Характеристики
    cuisine_type = Column(Enum(CuisineType), nullable=False, index=True)  # Тип кухни
    average_check = Column(Float, nullable=True)  # Средний чек в сумах
    has_booking = Column(Boolean, default=False, nullable=False)  # Есть ли возможность бронирования
    has_delivery = Column(Boolean, default=False, nullable=False)  # Есть ли доставка
    has_parking = Column(Boolean, default=False, nullable=False)  # Есть ли парковка
    has_wifi = Column(Boolean, default=False, nullable=False)  # Есть ли Wi-Fi
    
    # Рейтинг и статистика
    rating = Column(Float, default=0.0, nullable=False, index=True)  # Средний рейтинг
    reviews_count = Column(Integer, default=0, nullable=False)  # Количество отзывов
    
    # Статус и модерация
    status = Column(Enum(RestaurantStatus), default=RestaurantStatus.PENDING, nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если пользователь)
    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал (если админ)
    
    # Дополнительная информация
    category = Column(String, default="Ресторан", nullable=False)  # Категория
    description = Column(Text, nullable=True)  # Описание ресторана
    has_promotions = Column(Boolean, default=False, nullable=False, index=True)  # Есть ли акции
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)  # Когда был одобрен
    
    # Связи
    menu_categories = relationship("MenuCategory", back_populates="restaurant", cascade="all, delete-orphan")
    photos = relationship("RestaurantPhoto", back_populates="restaurant", cascade="all, delete-orphan")
    reviews = relationship("RestaurantReview", back_populates="restaurant", cascade="all, delete-orphan")
    
    # Индексы для геопоиска
    __table_args__ = (
        Index('idx_restaurant_location', 'latitude', 'longitude'),
    )


class MenuCategory(Base):
    """Модель категории меню"""
    __tablename__ = "menu_categories"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    
    name = Column(String, nullable=False)  # Название категории (например, "Супы", "Горячие блюда")
    description = Column(Text, nullable=True)  # Описание категории
    order = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    restaurant = relationship("Restaurant", back_populates="menu_categories")
    items = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan")


class MenuItem(Base):
    """Модель блюда в меню"""
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("menu_categories.id"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    
    name = Column(String, nullable=False)  # Название блюда
    description = Column(Text, nullable=True)  # Описание блюда
    price = Column(Float, nullable=False)  # Цена в сумах
    image_url = Column(String, nullable=True)  # URL фотографии блюда
    is_available = Column(Boolean, default=True, nullable=False)  # Доступно ли блюдо
    weight = Column(String, nullable=True)  # Вес/порция (например, "300г", "1 порция")
    calories = Column(Integer, nullable=True)  # Калории
    order = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    category = relationship("MenuCategory", back_populates="items")
    
    # Индексы
    __table_args__ = (
        Index('idx_menu_item_restaurant', 'restaurant_id'),
    )


class RestaurantPhoto(Base):
    """Модель фотографии ресторана"""
    __tablename__ = "restaurant_photos"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    
    photo_url = Column(String, nullable=False)  # URL фотографии
    is_main = Column(Boolean, default=False, nullable=False)  # Главная фотография
    order = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Кто загрузил
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    restaurant = relationship("Restaurant", back_populates="photos")


class RestaurantReview(Base):
    """Модель отзыва о ресторане"""
    __tablename__ = "restaurant_reviews"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    rating = Column(Integer, nullable=False)  # Рейтинг от 1 до 5
    comment = Column(Text, nullable=True)  # Текст отзыва
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    restaurant = relationship("Restaurant", back_populates="reviews")
    
    # Уникальность: один отзыв от пользователя на ресторан
    __table_args__ = (
        Index('idx_restaurant_review_unique', 'restaurant_id', 'user_id', unique=True),
    )











