# API для пользователя — все запросы

Базовый URL: `{BASE_URL}/api/v1`  
Авторизация: `Authorization: Bearer <token>` (кроме эндпоинтов без токена)

---

## 1. Авторизация

### Отправить код на телефон

```
POST /auth/send-code
```

Body: `{"phone_number": "+998901234567"}`

---

### Подтвердить код (вход/регистрация)

```
POST /auth/verify-code
```

Body: `{"phone_number": "+998901234567", "code": "1234"}`  
Ответ: `token` (JWT)

---

### Проверить регистрацию

```
POST /auth/check-registration
```

Body: `{"phone_number": "+998901234567"}`  
Ответ: `is_registered`, `phone_number`

---

### Вход по коду

```
POST /auth/login
```

Body: `{"phone_number": "+998901234567", "code": "1234"}`  
Ответ: `access_token`, `token_type`

---

### Выход

```
POST /auth/logout
Authorization: Bearer <token>
```

---

## 2. Профиль

### Получить профиль

```
GET /profile
Authorization: Bearer <token>
```

---

### Обновить имя

```
PATCH /profile/name
Authorization: Bearer <token>
```

Body: `{"name": "Иван"}`

---

### Обновить email

```
PATCH /profile/email
Authorization: Bearer <token>
```

Body: `{"email": "user@example.com"}`

---

### Загрузить паспорт

```
PATCH /profile/passport
Authorization: Bearer <token>
```

Form-data: `file` (изображение)

---

### Загрузить водительские права

```
PATCH /profile/driving-license
Authorization: Bearer <token>
```

Form-data: `file` (изображение)

---

### Настройки уведомлений

```
PATCH /profile/notifications
Authorization: Bearer <token>
```

Body: `{"notifications_enabled": true}`

---

### Загрузить аватар

```
PATCH /profile/avatar
Authorization: Bearer <token>
```

Form-data: `file` (изображение)

---

## 3. Избранное

### Список избранного

```
GET /favorites
GET /favorites?favorite_type=fuel_station
Authorization: Bearer <token>
```

Типы: `fuel_station`, `restaurant`, `car_service`, `car_wash`, `charging_station`

---

### Добавить в избранное

```
POST /favorites
Authorization: Bearer <token>
```

Body: `{"favorite_type": "fuel_station", "place_id": 5}`

---

### Удалить из избранного

```
DELETE /favorites/{favorite_type}/{place_id}
Authorization: Bearer <token>
```

---

### Проверить избранное

```
GET /favorites/check/{favorite_type}/{place_id}
Authorization: Bearer <token>
```

Ответ: `{"is_favorite": true/false}`

---

## 4. Уведомления

### Список уведомлений

```
GET /notifications?skip=0&limit=50
Authorization: Bearer <token>
```

---

### Статистика уведомлений

```
GET /notifications/stats
Authorization: Bearer <token>
```

---

### Отметить как прочитанное

```
PATCH /notifications/{notification_id}/read
Authorization: Bearer <token>
```

---

### Отметить все как прочитанные

```
POST /notifications/read-all
Authorization: Bearer <token>
```

---

### Удалить уведомление

```
DELETE /notifications/{notification_id}
Authorization: Bearer <token>
```

---

### Удалить все уведомления

```
DELETE /notifications
Authorization: Bearer <token>
```

---

## 5. Техподдержка

### Создать обращение

```
POST /support
Authorization: Bearer <token>
```

Body: `{"subject": "Тема", "message": "Текст сообщения"}`

---

### Список моих обращений

```
GET /support?skip=0&limit=50
Authorization: Bearer <token>
```

---

### Обращение по ID (с сообщениями)

```
GET /support/{ticket_id}
Authorization: Bearer <token>
```

---

### Добавить сообщение в обращение

```
POST /support/{ticket_id}/messages
Authorization: Bearer <token>
```

Body: `{"message": "Текст сообщения"}`

---

### Отметить обращение как прочитанное

```
POST /support/{ticket_id}/read
Authorization: Bearer <token>
```

---

## 6. Глобальный чат

### Отправить сообщение

```
POST /global-chat/messages
Authorization: Bearer <token>
```

Body: `{"content": "Текст", "message_type": "text"}`

---

### Загрузить файл в чат

```
POST /global-chat/messages/upload
Authorization: Bearer <token>
```

Form-data: `file`

---

### История сообщений

```
GET /global-chat/messages?skip=0&limit=50
Authorization: Bearer <token>
```

---

### Поиск сообщений

```
GET /global-chat/messages/search?query=текст
Authorization: Bearer <token>
```

---

### Онлайн пользователи

```
GET /global-chat/online
Authorization: Bearer <token>
```

---

### Заблокировать пользователя

```
POST /global-chat/block
Authorization: Bearer <token>
```

Body: `{"blocked_user_id": 5}`

---

### Разблокировать пользователя

```
DELETE /global-chat/block/{blocked_user_id}
Authorization: Bearer <token>
```

---

### Список заблокированных

```
GET /global-chat/blocked
Authorization: Bearer <token>
```

---

### Очистить историю чата

```
DELETE /global-chat/messages/history
Authorization: Bearer <token>
```

---

### Удалить сообщение

```
DELETE /global-chat/messages/{message_id}
Authorization: Bearer <token>
```

---

## 7. Заправки (gas-stations)

### Список заправок

```
GET /gas-stations/?skip=0&limit=100&fuel_type=AI-95&min_rating=4
Authorization: Bearer <token>
```

Фильтры: `fuel_type`, `min_rating`, `max_price`, `is_24_7`, `has_promotions`, `search_query`, `latitude`, `longitude`, `radius_km`

---

### Избранные заправки

```
GET /gas-stations/favorites
Authorization: Bearer <token>
```

---

### Добавить в избранное

```
POST /gas-stations/{station_id}/favorite
Authorization: Bearer <token>
```

---

### Удалить из избранного

```
DELETE /gas-stations/{station_id}/favorite
Authorization: Bearer <token>
```

---

### Детали заправки

```
GET /gas-stations/{station_id}
Authorization: Bearer <token>
```

---

### Создать заправку (модерация)

```
POST /gas-stations/
Authorization: Bearer <token>
```

---

### Редактировать заправку

```
PUT /gas-stations/{station_id}
Authorization: Bearer <token>
```

---

### Фото, цены, отзывы

- `POST /gas-stations/{station_id}/photos` — загрузить фото
- `DELETE /gas-stations/{station_id}/photos/{photo_id}` — удалить фото
- `POST /gas-stations/{station_id}/fuel-prices` — обновить цены
- `POST /gas-stations/{station_id}/reviews` — отзыв
- `PUT /gas-stations/{station_id}/reviews/{review_id}` — изменить отзыв
- `DELETE /gas-stations/{station_id}/reviews/{review_id}` — удалить отзыв

---

## 8. Рестораны (restaurants)

### Список

```
GET /restaurants/?skip=0&limit=100&cuisine_type=Узбекская
Authorization: Bearer <token>
```

Фильтры: `cuisine_type`, `min_rating`, `has_delivery`, `search_query`, `latitude`, `longitude`, `radius_km` и др.

---

### Избранные

```
GET /restaurants/favorites
POST /restaurants/{restaurant_id}/favorite
DELETE /restaurants/{restaurant_id}/favorite
Authorization: Bearer <token>
```

---

### Детали

```
GET /restaurants/{restaurant_id}
Authorization: Bearer <token>
```

---

### Меню, фото, отзывы

- `GET /restaurants/{id}/menu/categories`
- `GET /restaurants/{id}/menu/categories/{cat_id}/items`
- `POST /restaurants/{id}/photos`
- `POST /restaurants/{id}/reviews`

---

## 9. СТО (service-stations)

### Список

```
GET /service-stations/?skip=0&limit=100&service_type=Замена%20масла
Authorization: Bearer <token>
```

---

### Избранные

```
GET /service-stations/favorites
POST /service-stations/{station_id}/favorite
DELETE /service-stations/{station_id}/favorite
Authorization: Bearer <token>
```

---

### Детали, отзывы

```
GET /service-stations/{station_id}
POST /service-stations/{station_id}/reviews
```

---

## 10. Автомойки (car-washes)

### Список

```
GET /car-washes/?skip=0&limit=100&service_type=Ручная%20мойка
Authorization: Bearer <token>
```

---

### Избранные

```
GET /car-washes/favorites
POST /car-washes/{car_wash_id}/favorite
DELETE /car-washes/{car_wash_id}/favorite
Authorization: Bearer <token>
```

---

### Детали, отзывы

```
GET /car-washes/{car_wash_id}
POST /car-washes/{car_wash_id}/reviews
```

---

## 11. Электрозаправки (electric-stations)

### Список

```
GET /electric-stations/?skip=0&limit=100&connector_type=Type%202
Authorization: Bearer <token>
```

---

### Избранные

```
GET /electric-stations/favorites
POST /electric-stations/{station_id}/favorite
DELETE /electric-stations/{station_id}/favorite
Authorization: Bearer <token>
```

---

### Детали, отзывы

```
GET /electric-stations/{station_id}
POST /electric-stations/{station_id}/reviews
```

---

## 12. Реклама (advertisements)

### Список рекламы

```
GET /advertisements/?position=home_banner
```

Параметр `position`: `home_banner`, `gas_station_detail`, и др. Токен опционален.

---

### Зарегистрировать просмотр

```
POST /advertisements/{advertisement_id}/view
```

Body: `{"position": "home_banner"}` (опционально)

---

### Зарегистрировать клик

```
POST /advertisements/{advertisement_id}/click
```

---

## 13. Регионы (regions)

### Список регионов

```
GET /regions
GET /regions?is_active=true
```

Токен не требуется.

---

### Регион по ID

```
GET /regions/{region_id}
```

---

## 14. Доставка (delivery)

### Расчёт стоимости

```
POST /delivery/calculate-price
```

Body: `{"pickup": {...}, "dropoff": {...}}`

---

### Создать заказ

```
POST /delivery/orders
Authorization: Bearer <token>
```

Body: `{"pickup": {...}, "dropoff": {...}, "parcel_description": "...", "parcel_estimated_value": 100000}`

---

### Мои заказы

```
GET /delivery/orders?skip=0&limit=50&status=created
Authorization: Bearer <token>
```

---

### Заказ по ID

```
GET /delivery/orders/{order_id}
Authorization: Bearer <token>
```

---

### Отменить заказ

```
POST /delivery/orders/{order_id}/cancel
Authorization: Bearer <token>
```

Body (опц.): `{"reason": "Причина"}`

---

### Баланс

```
GET /delivery/balance
Authorization: Bearer <token>
```

---

### История по балансу

```
GET /delivery/balance/log?skip=0&limit=50
Authorization: Bearer <token>
```

---

## 15. Водители (drivers)

### Регистрация как водитель

```
POST /drivers/register
Authorization: Bearer <token>
```

Body: `{"phone_number": "+998...", "full_name": "...", "email": "...", "region_id": 1}`

---

### Мой профиль водителя

```
GET /drivers/me
PUT /drivers/me
Authorization: Bearer <token>
```

---

### Документы и ТС

- `POST /drivers/me/documents` — добавить документ
- `GET /drivers/me/documents`
- `PUT /drivers/me/vehicle` — данные ТС
- `PATCH /drivers/me/online` — статус онлайн

---

## 16. Доставка: водитель (delivery/driver)

*Для пользователей, зарегистрированных как водители.*

- `GET /delivery/driver/orders` — мои заказы
- `GET /delivery/driver/orders/{id}` — заказ по ID
- `POST /delivery/driver/orders/{id}/accept` — принять заказ
- `POST /delivery/driver/orders/{id}/reject` — отклонить заказ
- `PATCH /delivery/driver/orders/{id}/status` — обновить статус

---

## Сводная таблица

| Раздел | Prefix | Основные методы |
|--------|--------|-----------------|
| Авторизация | `/auth` | send-code, verify-code, login, logout |
| Профиль | `/profile` | GET, PATCH name/email/passport/driving-license/avatar |
| Избранное | `/favorites` | GET, POST, DELETE |
| Уведомления | `/notifications` | GET, PATCH read, DELETE |
| Поддержка | `/support` | POST ticket, GET, POST messages |
| Глобальный чат | `/global-chat` | messages, block, online |
| Заправки | `/gas-stations` | GET list/favorites, POST favorite |
| Рестораны | `/restaurants` | GET list/favorites, POST favorite |
| СТО | `/service-stations` | GET list/favorites, POST favorite |
| Автомойки | `/car-washes` | GET list/favorites, POST favorite |
| Электрозаправки | `/electric-stations` | GET list/favorites, POST favorite |
| Реклама | `/advertisements` | GET, POST view/click |
| Регионы | `/regions` | GET (без токена) |
| Доставка | `/delivery` | calculate-price, orders |
| Водители | `/drivers` | register, me |
