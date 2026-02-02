# Инструкция по API доставки

Базовый URL: `{BASE_URL}/api/v1`  
Авторизация: `Authorization: Bearer <token>`

---

## 1. Пользователь (клиент)

### Расчёт стоимости

```
POST /delivery/calculate-price
```

Body:
```json
{
  "pickup": {
    "latitude": 41.3111,
    "longitude": 69.2797,
    "address": "Ташкент, ул. Навои 1"
  },
  "dropoff": {
    "latitude": 41.3150,
    "longitude": 69.2800,
    "address": "Ташкент, ул. Амира Темура 15"
  }
}
```

Ответ: `distance_km`, `delivery_cost`, `min_total`, `cost_per_km`, `base_fixed`

---

### Создать заказ

```
POST /delivery/orders
```

Body:
```json
{
  "pickup": {
    "latitude": 41.3111,
    "longitude": 69.2797,
    "address": "Ташкент, ул. Навои 1"
  },
  "dropoff": {
    "latitude": 41.3150,
    "longitude": 69.2800,
    "address": "Ташкент, ул. Амира Темура 15"
  },
  "parcel_description": "Документы",
  "parcel_estimated_value": 100000
}
```

- Списание с баланса при создании
- Статус заказа: `created` (ожидает назначения водителя админом)

---

### Мои заказы

```
GET /delivery/orders?skip=0&limit=50&status=created
```

Параметры: `skip`, `limit`, `status` (опционально)

---

### Заказ по ID

```
GET /delivery/orders/{order_id}
```

---

### Отменить заказ

```
POST /delivery/orders/{order_id}/cancel
```

Body (опционально): `{"reason": "Причина"}`  
Доступно до статуса `picked_up`. Деньги возвращаются на баланс.

---

### Баланс

```
GET /delivery/balance
```

Ответ: `{"balance": 0.0}`

---

### История по балансу

```
GET /delivery/balance/log?skip=0&limit=50
```

---

## 2. Водитель

### Мои заказы

```
GET /delivery/driver/orders?skip=0&limit=50&status=driver_assigned
```

---

### Заказ по ID

```
GET /delivery/driver/orders/{order_id}
```

---

### Принять заказ

```
POST /delivery/driver/orders/{order_id}/accept
```

---

### Отклонить заказ

```
POST /delivery/driver/orders/{order_id}/reject
```

Заказ возвращается в `created` для повторного назначения админом.

---

### Обновить статус

```
PATCH /delivery/driver/orders/{order_id}/status
```

Body: `{"status": "driver_on_way"}`  
Допустимые: `driver_on_way` → `picked_up` → `in_delivery` → `delivered`

---

## 3. Администратор

### Тарифы

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/admin/delivery/tariffs` | Создать тариф |
| GET | `/admin/delivery/tariffs` | Список тарифов |
| GET | `/admin/delivery/tariffs/{id}` | Тариф по ID |
| PUT | `/admin/delivery/tariffs/{id}` | Изменить тариф |
| DELETE | `/admin/delivery/tariffs/{id}` | Удалить тариф |

Создание тарифа:
```json
{
  "name": "По городу",
  "cost_per_km": 500,
  "min_total": 5000,
  "base_fixed": 2000,
  "is_active": true
}
```

---

### Заказы

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/admin/delivery/orders` | Все заказы (skip, limit, status, user_id) |
| GET | `/admin/delivery/orders/{id}` | Заказ по ID |
| POST | `/admin/delivery/orders/{id}/assign-driver` | Назначить водителя |
| POST | `/admin/delivery/orders/{id}/cancel` | Отменить заказ |

Назначение водителя (заказ в статусе `created`):
```json
{"driver_id": 5}
```

---

## 4. Статусы заказа

```
created → driver_assigned → driver_on_way → picked_up → in_delivery → delivered → completed
```

Отмена: `canceled` (пользователь — до `picked_up`, админ — в любой момент)

| Статус | Описание |
|--------|----------|
| created | Ожидает назначения водителя админом |
| driver_assigned | Водитель назначен |
| driver_on_way | Водитель едет к точке забора |
| picked_up | Посылка получена водителем |
| in_delivery | Посылка в доставке |
| delivered | Доставлено |
| completed | Заказ завершён |
| canceled | Отменён |
