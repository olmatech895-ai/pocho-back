# API Ресторанов — краткая инструкция

Базовый URL: `{BASE_URL}/api/v1`  
Все эндпоинты требуют авторизации: `Authorization: Bearer <token>`

---

## Получение ресторанов

### Список ресторанов с фильтрацией

```
GET /restaurants/
```

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| skip | int | Смещение (по умолчанию 0) |
| limit | int | Лимит (1–1000, по умолчанию 100) |
| cuisine_type | str | Тип кухни (Узбекская, Европейская, Фастфуд и др.) |
| min_rating | float | Минимальный рейтинг (0–5) |
| min_average_check | float | Минимальный средний чек |
| max_average_check | float | Максимальный средний чек |
| is_24_7 | bool | Круглосуточные |
| has_promotions | bool | Есть акции |
| has_booking | bool | Есть бронирование |
| has_delivery | bool | Есть доставка |
| has_parking | bool | Есть парковка |
| has_wifi | bool | Есть Wi‑Fi |
| search_query | str | Поиск по названию или адресу |
| latitude | float | Широта (поиск рядом) |
| longitude | float | Долгота |
| radius_km | float | Радиус в км |

**Пример:**
```
GET /restaurants/?skip=0&limit=20&cuisine_type=Узбекская&has_delivery=true
```

### Детали ресторана

```
GET /restaurants/{restaurant_id}
```

---

## Избранные рестораны

### Получить избранные рестораны

```
GET /restaurants/favorites
```

**Query-параметры:** `skip`, `limit` (по умолчанию 0 и 100)

### Добавить в избранное

```
POST /restaurants/{restaurant_id}/favorite
```

**Ответ (201):** `{"message": "Добавлено в избранное", "id": 123}`

### Удалить из избранного

```
DELETE /restaurants/{restaurant_id}/favorite
```

**Ответ:** 204 No Content

---

## Общий API избранного (все типы)

```
GET  /favorites                    — все избранное
GET  /favorites?favorite_type=restaurant — только рестораны
POST /favorites                    — body: {"favorite_type": "restaurant", "place_id": 5}
DELETE /favorites/restaurant/{place_id}
GET  /favorites/check/restaurant/{place_id} — {"is_favorite": true/false}
```
