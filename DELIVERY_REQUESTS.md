# Запросы доставки: клиент и админ

Базовый URL: `https://ваш-сервер/api/v1`  
Авторизация: заголовок `Authorization: Bearer <токен>`.

---

## 1. Клиент (мобильное приложение / пользователь)

Токен — после входа пользователя (`/auth/...`).

### 1.1. Рассчитать стоимость доставки

**POST** `/delivery/calculate-price`  
Тело:
```json
{
  "pickup": {
    "latitude": 41.3,
    "longitude": 69.2,
    "address": "Откуда забрать (адрес или описание)"
  },
  "dropoff": {
    "latitude": 41.35,
    "longitude": 69.3,
    "address": "Куда доставить"
  }
}
```
Ответ: `distance_km`, `delivery_cost`, `min_total`, `cost_per_km`, `base_fixed`.

---

### 1.2. Создать заказ

**POST** `/delivery/orders`  
Тело:
```json
{
  "pickup": {
    "latitude": 41.3,
    "longitude": 69.2,
    "address": "Адрес точки забора"
  },
  "dropoff": {
    "latitude": 41.35,
    "longitude": 69.3,
    "address": "Адрес точки доставки"
  },
  "parcel_description": "Описание посылки",
  "parcel_estimated_value": 100000
}
```
При недостаточном балансе — ошибка 400. При успехе — списание с баланса, создание заказа, поиск водителя.

---

### 1.3. Мои заказы

**GET** `/delivery/orders?skip=0&limit=50&status=created`  
Параметры (все необязательные): `skip`, `limit`, `status` (created, searching_driver, driver_assigned, driver_on_way, picked_up, in_delivery, delivered, completed, canceled).

---

### 1.4. Заказ по ID

**GET** `/delivery/orders/{id}`  
Только свои заказы.

---

### 1.5. Отменить заказ

**POST** `/delivery/orders/{id}/cancel`  
Тело (необязательно): `{"reason": "Причина отмены"}`.  
Доступно до момента, когда водитель получил посылки (до статуса `picked_up`). Деньги возвращаются на баланс.

---

### 1.6. Баланс

**GET** `/delivery/balance`  
Ответ: `{"balance": 0.0}`.

---

### 1.7. История по балансу

**GET** `/delivery/balance/log?skip=0&limit=50`  
Ответ: список записей (order_id, amount, type, description, created_at).

---

## 2. Админ

Токен — после входа под учётной записью с правами администратора.

### 2.1. Тарифы

**Создать тариф**  
**POST** `/admin/delivery/tariffs`  
Тело:
```json
{
  "name": "По городу",
  "cost_per_km": 500,
  "min_total": 5000,
  "base_fixed": 2000,
  "extra_coefficients": null,
  "is_active": true
}
```

**Список тарифов**  
**GET** `/admin/delivery/tariffs?skip=0&limit=100&is_active=true`

**Тариф по ID**  
**GET** `/admin/delivery/tariffs/{id}`

**Изменить тариф**  
**PUT** `/admin/delivery/tariffs/{id}`  
Тело (все поля необязательные): `name`, `cost_per_km`, `min_total`, `base_fixed`, `extra_coefficients`, `is_active`.

**Удалить тариф**  
**DELETE** `/admin/delivery/tariffs/{id}`  
Ответ: 204 без тела.

---

### 2.2. Заказы

**Список всех заказов**  
**GET** `/admin/delivery/orders?skip=0&limit=100&status=created&user_id=7`  
Параметры (необязательные): `skip`, `limit`, `status`, `user_id`.

**Заказ по ID**  
**GET** `/admin/delivery/orders/{id}`

**Назначить водителя**  
**POST** `/admin/delivery/orders/{id}/assign-driver`  
Тело: `{"driver_id": 5}`  
Заказ должен быть в статусе `created`. Водитель должен быть одобрен (APPROVED).

**Отменить заказ**  
**POST** `/admin/delivery/orders/{id}/cancel`  
Тело (необязательно): `{"reason": "Причина отмены"}`.  
Доступно на любом этапе. Деньги возвращаются на баланс клиента.

---

## Статусы заказа

`created` → `driver_assigned` → `driver_on_way` → `picked_up` → `in_delivery` → `delivered` → `completed`  
Либо `canceled` (отмена клиентом до получения посылки водителем или отмена админом в любой момент).
