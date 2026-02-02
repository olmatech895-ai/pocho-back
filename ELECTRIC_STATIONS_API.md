# API Электрозаправок — краткая инструкция

Базовый URL: `{BASE_URL}/api/v1`  
Все эндпоинты требуют авторизации: `Authorization: Bearer <token>`

---

## Получение электрозаправок

### Список электрозаправок с фильтрацией

```
GET /electric-stations/
```

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| skip | int | Смещение (по умолчанию 0) |
| limit | int | Лимит (1–1000, по умолчанию 100) |
| connector_type | str | Тип разъёма (Type 1, Type 2, CCS Type 1, CHAdeMO и др.) |
| min_power_kw | float | Минимальная мощность (кВт) |
| max_power_kw | float | Максимальная мощность (кВт) |
| min_price_per_kwh | float | Минимальная цена за кВт·ч |
| max_price_per_kwh | float | Максимальная цена за кВт·ч |
| min_rating | float | Минимальный рейтинг (0–5) |
| is_24_7 | bool | Круглосуточные |
| has_promotions | bool | Есть акции |
| has_parking | bool | Есть парковка |
| has_waiting_room | bool | Есть комната ожидания |
| has_cafe | bool | Есть кафе |
| has_restroom | bool | Есть туалет |
| accepts_cards | bool | Принимают карты |
| has_mobile_app | bool | Есть мобильное приложение |
| requires_membership | bool | Требуется членство |
| has_available_points | bool | Есть свободные точки |
| operator | str | Оператор |
| network | str | Сеть |
| search_query | str | Поиск по названию или адресу |
| latitude | float | Широта (поиск рядом) |
| longitude | float | Долгота |
| radius_km | float | Радиус в км |

**Типы разъёмов:** Type 1, Type 2, CCS Type 1, CCS Type 2, CHAdeMO, Tesla Supercharger, Tesla Destination, GB/T, Другое

**Пример:**
```
GET /electric-stations/?skip=0&limit=20&connector_type=Type%202&has_parking=true
```

### Детали электрозаправки

```
GET /electric-stations/{station_id}
```

---

## Избранные электрозаправки

### Получить избранные электрозаправки

```
GET /electric-stations/favorites
```

**Query-параметры:** `skip`, `limit` (по умолчанию 0 и 100)

### Добавить в избранное

```
POST /electric-stations/{station_id}/favorite
```

**Ответ (201):** `{"message": "Добавлено в избранное", "id": 123}`

### Удалить из избранного

```
DELETE /electric-stations/{station_id}/favorite
```

**Ответ:** 204 No Content

---

## Общий API избранного (все типы)

```
GET  /favorites                             — все избранное
GET  /favorites?favorite_type=charging_station — только электрозаправки
POST /favorites                             — body: {"favorite_type": "charging_station", "place_id": 5}
DELETE /favorites/charging_station/{place_id}
GET  /favorites/check/charging_station/{place_id} — {"is_favorite": true/false}
```
