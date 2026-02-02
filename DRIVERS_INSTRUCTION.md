# Инструкция по API водителей и доставки

Базовый URL: `{BASE_URL}/api/v1`

---

## 1. Статусы водителя

| Статус | Описание | Кто назначает | Может принимать заказы? |
|--------|----------|---------------|-------------------------|
| `pending` | Ожидает проверки документов | система (при регистрации) | Нет |
| `approved` | Одобрен, может работать | админ | Да |
| `rejected` | Отклонён администратором | админ | Нет |
| `suspended` | Временно заблокирован | админ | Нет |
| `offline` | Одобрен, не в сети | водитель (себя) | Нет |
| `online` | В сети, готов к заказам | водитель (себя) | Да |

**Логика:**
- `pending`, `rejected`, `suspended` — водитель не может выходить в сеть
- `approved` — базовый статус после одобрения
- `offline` / `online` — водитель переключает сам (выйти/выйти в сеть)

---

## 2. Водитель (пользователь) — смена своего статуса

### Выйти в сеть / выйти из сети

```
POST /drivers/me/online-status
PATCH /drivers/me/status
Authorization: Bearer <token>
```

Body:
```json
{"is_online": true}
```
или
```json
{"is_online": false}
```

- `is_online: true` → статус `online`
- `is_online: false` → статус `offline`

**Ограничения:** Доступно только при статусе `approved`, `online` или `offline`. При `pending`, `rejected`, `suspended` — ошибка 400.

---

## 3. Администратор — назначение водителя на заказ

### Назначить водителя на заказ доставки

```
POST /admin/delivery/orders/{order_id}/assign-driver
Authorization: Bearer <admin_token>
```

Body:
```json
{"driver_id": 5}
```

**Условия:**
- Заказ в статусе `created`
- Водитель в статусе `approved`, `online` или `offline`

**Ошибка 400** — если:
- Заказ не в статусе `created`
- Водитель не найден
- Водитель в статусе `pending`, `rejected`, `suspended`

---

## 4. Администратор — управление водителями

### Список водителей

```
GET /admin/drivers?skip=0&limit=100&status=approved&is_online=true
Authorization: Bearer <admin_token>
```

Параметры: `status`, `is_online`, `region_id`, `search`

### Смена статуса водителя

```
PUT /admin/drivers/{driver_id}/status
Authorization: Bearer <admin_token>
```

Body:
```json
{
  "status": "approved",
  "admin_comment": "Документы проверены"
}
```

Допустимые значения: `pending`, `approved`, `rejected`, `suspended`, `offline`, `online`

---

## 5. Типовой сценарий

### Регистрация и одобрение

1. Пользователь: `POST /drivers/register` → водитель со статусом `pending`
2. Админ: проверяет документы, `PUT /admin/drivers/{id}/status` с `status: "approved"`
3. Водитель: `PATCH /drivers/me/status` с `{"is_online": true}` → статус `online`

### Назначение на заказ

1. Пользователь создаёт заказ: `POST /delivery/orders` → статус заказа `created`
2. Админ получает список: `GET /admin/delivery/orders?status=created`
3. Админ смотрит водителей: `GET /admin/drivers?status=approved` (или `online`/`offline`)
4. Админ назначает: `POST /admin/delivery/orders/{order_id}/assign-driver` с `{"driver_id": 5}`

### Работа водителя

1. Водитель: `GET /delivery/driver/orders` — видит назначенные заказы
2. Принять: `POST /delivery/driver/orders/{id}/accept`
3. Обновить статус: `PATCH /delivery/driver/orders/{id}/status` с `{"status": "driver_on_way"}` и т.д.

---

## 6. Краткая справка по эндпоинтам

### Водитель (пользователь)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/drivers/register` | Регистрация как водитель |
| GET | `/drivers/me` | Мой профиль |
| PUT | `/drivers/me` | Обновить профиль |
| POST | `/drivers/me/online-status` | Сменить онлайн (body: `{"is_online": true/false}`) |
| PATCH | `/drivers/me/status` | То же (body: `{"is_online": true/false}`) |
| GET | `/drivers/me/statistics` | Статистика |
| GET | `/delivery/driver/orders` | Мои заказы доставки |
| POST | `/delivery/driver/orders/{id}/accept` | Принять заказ |
| POST | `/delivery/driver/orders/{id}/reject` | Отклонить заказ |
| PATCH | `/delivery/driver/orders/{id}/status` | Обновить статус заказа |

### Администратор

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/admin/drivers` | Список водителей |
| GET | `/admin/drivers/{id}` | Водитель по ID |
| PUT | `/admin/drivers/{id}/status` | Сменить статус водителя |
| GET | `/admin/delivery/orders` | Список заказов |
| POST | `/admin/delivery/orders/{id}/assign-driver` | Назначить водителя |
