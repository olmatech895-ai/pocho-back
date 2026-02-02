# API Автомоек — краткая инструкция

Базовый URL: `{BASE_URL}/api/v1`  
Все эндпоинты требуют авторизации: `Authorization: Bearer <token>`

---

## Получение автомоек

### Список автомоек с фильтрацией

```
GET /car-washes/
```

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| skip | int | Смещение (по умолчанию 0) |
| limit | int | Лимит (1–1000, по умолчанию 100) |
| service_type | str | Тип услуги (Ручная мойка, Автоматическая мойка, Химчистка и др.) |
| min_rating | float | Минимальный рейтинг (0–5) |
| min_price | float | Минимальная цена |
| max_price | float | Максимальная цена |
| is_24_7 | bool | Круглосуточные |
| has_promotions | bool | Есть акции |
| has_parking | bool | Есть парковка |
| has_waiting_room | bool | Есть комната ожидания |
| has_cafe | bool | Есть кафе |
| accepts_cards | bool | Принимают карты |
| has_vacuum | bool | Есть пылесос |
| has_drying | bool | Есть сушка |
| has_self_service | bool | Есть самообслуживание |
| search_query | str | Поиск по названию или адресу |
| latitude | float | Широта (поиск рядом) |
| longitude | float | Долгота |
| radius_km | float | Радиус в км |

**Типы услуг:** Ручная мойка, Автоматическая мойка, Химчистка, Полировка, Нанесение воска, Пылесос, Мойка двигателя, Мойка днища, Чистка салона, Обработка кожи, Чистка шин, Другое

**Пример:**
```
GET /car-washes/?skip=0&limit=20&service_type=Ручная%20мойка&has_parking=true
```

### Детали автомойки

```
GET /car-washes/{car_wash_id}
```

---

## Избранные автомойки

### Получить избранные автомойки

```
GET /car-washes/favorites
```

**Query-параметры:** `skip`, `limit` (по умолчанию 0 и 100)

### Добавить в избранное

```
POST /car-washes/{car_wash_id}/favorite
```

**Ответ (201):** `{"message": "Добавлено в избранное", "id": 123}`

### Удалить из избранного

```
DELETE /car-washes/{car_wash_id}/favorite
```

**Ответ:** 204 No Content

---

## Общий API избранного (все типы)

```
GET  /favorites                       — все избранное
GET  /favorites?favorite_type=car_wash — только автомойки
POST /favorites                       — body: {"favorite_type": "car_wash", "place_id": 5}
DELETE /favorites/car_wash/{place_id}
GET  /favorites/check/car_wash/{place_id} — {"is_favorite": true/false}
```
