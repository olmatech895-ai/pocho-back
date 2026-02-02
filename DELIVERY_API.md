# API доставки по ТЗ

## Модели и БД

- **UserExtended.balance** — единый баланс пользователя (Float, default=0). Используется для всех операций, включая доставку.
- **delivery_tariffs** — тарифы (cost_per_km, min_total, base_fixed, extra_coefficients).
- **delivery_orders** — заказы (точки, посылка, стоимость, статус, user_id, driver_id).
- **delivery_order_status_history** — история смены статусов (ТЗ п.7).
- **user_balance_logs** — движения по балансу (списание/возврат) для доставки.

**Важно:** Баланс хранится в таблице `users_extended` в поле `balance`. Это единый баланс пользователя для всех операций в системе (доставка, транзакции и т.д.).

**Миграция:** Если у вас были балансы в `users.balance`, запустите скрипт миграции:
```bash
python scripts/migrate_balance_to_extended.py
```

## Запросы

### Пользователь (Bearer-токен)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/delivery/calculate-price` | Расчёт стоимости (pickup, dropoff) — ТЗ п.2.4 |
| POST | `/api/v1/delivery/orders` | Создать заказ (проверка баланса, списание) — ТЗ п.4 |
| GET | `/api/v1/delivery/orders` | Мои заказы (skip, limit, status) |
| GET | `/api/v1/delivery/orders/{id}` | Заказ по ID |
| POST | `/api/v1/delivery/orders/{id}/cancel` | Отмена (до получения посылки) — ТЗ п.8 |
| GET | `/api/v1/delivery/balance` | Баланс — ТЗ п.5 |
| GET | `/api/v1/delivery/balance/log` | История по балансу |

### Водитель (Bearer-токен, пользователь должен быть водителем)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/delivery/driver/orders` | Заказы, назначенные на водителя |
| GET | `/api/v1/delivery/driver/orders/{id}` | Заказ по ID |
| POST | `/api/v1/delivery/driver/orders/{id}/accept` | Принять заказ — ТЗ п.6.3 |
| POST | `/api/v1/delivery/driver/orders/{id}/reject` | Отклонить (поиск следующего) — ТЗ п.6.3 |
| PATCH | `/api/v1/delivery/driver/orders/{id}/status` | Смена статуса: driver_on_way, picked_up, in_delivery, delivered — ТЗ п.7 |

### Админ (Bearer-токен админа)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/admin/delivery/tariffs` | Создать тариф — ТЗ п.3 |
| GET | `/api/v1/admin/delivery/tariffs` | Список тарифов |
| GET | `/api/v1/admin/delivery/tariffs/{id}` | Тариф по ID |
| PUT | `/api/v1/admin/delivery/tariffs/{id}` | Обновить тариф |
| DELETE | `/api/v1/admin/delivery/tariffs/{id}` | Удалить тариф |
| GET | `/api/v1/admin/delivery/orders` | Все заказы (status, user_id) |
| GET | `/api/v1/admin/delivery/orders/{id}` | Заказ по ID |
| POST | `/api/v1/admin/delivery/orders/{id}/assign-driver` | Назначить водителя на заказ (body: `{"driver_id": 5}`) |
| POST | `/api/v1/admin/delivery/orders/{id}/cancel` | Отмена на любом этапе — ТЗ п.8 |

## Статусы заказа (ТЗ п.7)

created → driver_assigned → driver_on_way → picked_up → in_delivery → delivered → completed  
Либо canceled на допустимых этапах.

**Логика назначения водителя:** Заказ создаётся в статусе `created`. Администратор назначает водителя через `POST /admin/delivery/orders/{id}/assign-driver`. После назначения статус меняется на `driver_assigned`.

## Примеры тел запросов

**Расчёт цены:**  
`POST /api/v1/delivery/calculate-price`
```json
{
  "pickup": { "latitude": 41.3, "longitude": 69.2, "address": "Ташкент, ул. Примерная 1" },
  "dropoff": { "latitude": 41.35, "longitude": 69.3, "address": "Ташкент, ул. Другая 2" }
}
```

**Создание заказа:**  
`POST /api/v1/delivery/orders`
```json
{
  "pickup": { "latitude": 41.3, "longitude": 69.2, "address": "Откуда забрать" },
  "dropoff": { "latitude": 41.35, "longitude": 69.3, "address": "Куда доставить" },
  "parcel_description": "Документы",
  "parcel_estimated_value": 100000
}
```

**Создание тарифа (админ):**  
`POST /api/v1/admin/delivery/tariffs`
```json
{
  "name": "По городу",
  "cost_per_km": 500,
  "min_total": 5000,
  "base_fixed": 2000,
  "is_active": true
}
```

## Критерии приёмки ТЗ

1. Расчёт стоимости между двумя точками — `POST /delivery/calculate-price`.
2. Стоимость по тарифам — тариф задаётся админом, расчёт в `utils.apply_tariff`.
3. Заказ не создаётся при недостаточном балансе — проверка в `create_delivery_order`.
4. После создания заказа — администратор назначает водителя через `POST /admin/delivery/orders/{id}/assign-driver`.
5. Жизненный цикл заказа — статусы и история в `delivery_order_status_history`.
6. Отмена — пользователь до picked_up; админ в любой момент; возврат средств при отмене.
