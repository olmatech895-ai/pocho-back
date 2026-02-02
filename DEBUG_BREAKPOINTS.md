# Отладка страницы «По регионам Узбекистана»

Брейкпоинты **удалены из кода** — иначе запросы к API зависают (сервер останавливается в Pdb и не отдаёт ответ).

## Как отлаживать при необходимости

1. **Временно** добавьте в нужный эндпоинт одну строку:
   ```python
   breakpoint()
   ```
   Файлы: `app/api/v1/regions.py`, `app/api/v1/pricing.py`.

2. Запустите сервер **из терминала** (не в фоне):  
   `python run.py`  
   При вызове этого эндпоинта выполнение остановится в Pdb.

3. В Pdb: смотрите переменные (`query`, `db`, `region_id` и т.д.), шагайте (`n` — следующая строка, `c` — продолжить до конца).

4. **Обязательно удалите** `breakpoint()` после отладки — иначе приложение снова не будет получать ответы от API.

## Эндпоинты, которые можно так отлаживать

| Эндпоинт | Файл, функция |
|----------|----------------|
| `GET /api/v1/regions` | `regions.py` → `get_regions` |
| `GET /api/v1/regions/{id}` | `regions.py` → `get_region` |
| `GET /api/v1/pricing/package-sizes` | `pricing.py` → `get_package_sizes` |
| `GET /api/v1/pricing/package-sizes/with-prices` | `pricing.py` → `get_package_sizes_with_prices` |
| `POST /api/v1/pricing/calculate` | `pricing.py` → `calculate_delivery_price` |
