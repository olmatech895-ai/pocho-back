from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi import status
import logging
from pathlib import Path

from app.core.config import settings
from app.database import engine, Base
from app.api.v1 import api_router
from app.models import (
    User,
    VerificationCode,
    BlacklistedToken,
    UserExtended,
    UserProfile,
    UserFavorite,
    UserAchievement,
    UserNotification,
    Transaction,
    UserStatistics,
    Notification,
    NotificationReadStatus,
    SupportTicket,
    SupportMessage,
    GlobalChatMessage,
    UserBlock,
    HiddenGlobalChatMessage,
    GasStation,
    FuelPrice,
    GasStationPhoto,
    Review,
    Restaurant,
    MenuCategory,
    MenuItem,
    RestaurantPhoto,
    RestaurantReview,
    ServiceStation,
    ServicePrice,
    ServiceStationPhoto,
    ServiceStationReview,
    CarWash,
    CarWashService,
    CarWashPhoto,
    CarWashReview,
    Advertisement,
    AdvertisementView,
    AdvertisementClick,
    ElectricStation,
    ChargingPoint,
    ElectricStationPhoto,
    ElectricStationReview,
    Driver,
    DriverDocument,
    Vehicle,
    Region,
    DeliveryOrderStatus,
    DeliveryTariff,
    DeliveryOrder,
    DeliveryOrderStatusHistory,
    UserBalanceLog,
)
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_middleware import (
    SecurityHeadersMiddleware,
    RequestSizeMiddleware,
    ErrorHandlingMiddleware,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Pocho Backend API",
    description="API с авторизацией и интеграцией PostgreSQL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# Порядок важен! Middleware применяются в обратном порядке
# 1. ErrorHandlingMiddleware - последний, обрабатывает все ошибки
app.add_middleware(ErrorHandlingMiddleware)

# 2. SecurityHeadersMiddleware - добавляет заголовки безопасности
app.add_middleware(SecurityHeadersMiddleware)

# 3. RequestSizeMiddleware - ограничивает размер запросов
app.add_middleware(RequestSizeMiddleware)

# 4. RateLimitMiddleware - ограничивает частоту запросов
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# 5. CORS middleware - первый, обрабатывает CORS
cors_origins = (
    settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# Подключение роутеров
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Подключение статических файлов для загрузок
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)

# Создаем подпапки для разных типов медиа
subdirs = [
    "avatars",
    "passports",
    "driving_licenses",
    "global_chat/images",
    "global_chat/videos",
    "global_chat/audio",
    "global_chat/files",
    "gas_stations",
    "restaurants",
    "restaurants/menu_items",
    "service_stations",
    "car_washes",
    "advertisements",
    "electric_stations",
    "drivers/documents",
    "drivers/photos",
    "vehicles/photos",
]

for subdir in subdirs:
    (upload_dir / subdir).mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Глобальный обработчик ошибок валидации запросов
    Возвращает понятные сообщения об ошибках валидации
    """
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "Validation error")
        error_type = error.get("type", "")

        if error_type == "value_error.missing":
            errors.append(f"Поле '{field_path}' обязательно для заполнения")
        elif error_type == "type_error.str":
            errors.append(f"Поле '{field_path}' должно быть строкой")
        elif "phone_number" in field_path.lower() and "value_error" in error_type:
            if "uzbek" in str(msg).lower() or "998" in str(msg).lower():
                errors.append(
                    f"Неверный формат номера телефона. Используйте формат: +998XXXXXXXXX (например: +998900000000)"
                )
            else:
                errors.append(f"Поле '{field_path}': {msg}")
        else:
            errors.append(f"Поле '{field_path}': {msg}")

    detail = "; ".join(errors) if errors else "Ошибка валидации данных запроса"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": detail}
    )


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Добро пожаловать в Pocho Backend API",
        "docs": "/docs",
        "redoc": "/redoc",
    }
