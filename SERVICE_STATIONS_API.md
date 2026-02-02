# API СТО (Станций технического обслуживания) — краткая инструкция

Базовый URL: `{BASE_URL}/api/v1`  
Все эндпоинты требуют авторизации: `Authorization: Bearer <token>`

---

## Получение СТО

### Список СТО с фильтрацией

```
GET /service-stations/
```

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| skip | int | Смещение (по умолчанию 0) |
| limit | int | Лимит (1–1000, по умолчанию 100) |
| service_type | str | Тип услуги (Замена масла, Ремонт двигателя, Шиномонтаж и др.) |
| min_rating | float | Минимальный рейтинг (0–5) |
| min_price | float | Минимальная цена |
| max_price | float | Максимальная цена |
| is_24_7 | bool | Круглосуточные |
| has_promotions | bool | Есть акции |
| has_parking | bool | Есть парковка |
| has_waiting_room | bool | Есть комната ожидания |
| has_cafe | bool | Есть кафе |
| accepts_cards | bool | Принимают карты |
| search_query | str | Поиск по названию или адресу |
| latitude | float | Широта (поиск рядом) |
| longitude | float | Долгота |
| radius_km | float | Радиус в км |

**Типы услуг:** Замена масла, Ремонт двигателя, Ремонт КПП, Ремонт тормозов, Ремонт подвески, Ремонт электрооборудования, Шиномонтаж, Развал-схождение, Кузовной ремонт, Покраска, Диагностика, Техобслуживание, Мойка, Другое

**Пример:**
```
GET /service-stations/?skip=0&limit=20&service_type=Замена%20масла&has_parking=true
```

### Детали СТО

```
GET /service-stations/{station_id}
```

---

## Избранные СТО

### Получить избранные СТО

```
GET /service-stations/favorites
```

**Query-параметры:** `skip`, `limit` (по умолчанию 0 и 100)

### Добавить в избранное

```
POST /service-stations/{station_id}/favorite
```

**Ответ (201):** `{"message": "Добавлено в избранное", "id": 123}`

### Удалить из избранного

```
DELETE /service-stations/{station_id}/favorite
```

**Ответ:** 204 No Content

---

## Общий API избранного (все типы)

```
GET  /favorites                          — все избранное
GET  /favorites?favorite_type=car_service — только СТО
POST /favorites                          — body: {"favorite_type": "car_service", "place_id": 5}
DELETE /favorites/car_service/{place_id}
GET  /favorites/check/car_service/{place_id} — {"is_favorite": true/false}
```
