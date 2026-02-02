# Инструкция: экран «По регионам Узбекистана»

## 1. Админка (заполнение данных)

### 1.1 Регионы

Регионы сейчас **не редактируются через админку**. Варианты:

- **Добавить регионы скриптом:**  
  `python scripts/add_regions.py` — создаёт набор регионов Узбекистана в БД.
- **Вручную в БД:** таблица `regions` — поля `name_uz`, `name_ru`, `name_en`, `center_latitude`, `center_longitude`, `display_order`, `is_active`.

Чтобы в админке был раздел «Регионы», нужны эндпоинты вида:  
`GET/POST/PUT/DELETE /api/v1/admin/regions` (сейчас их нет).

---

### 1.2 Тарифы и цены (раздел «Админ: Тарифы и цены»)

Все запросы — с заголовком авторизации админа:  
`Authorization: Bearer <admin_access_token>`.

**Шаг 1 — размеры посылок**

- **Создать размер:**  
  `POST /api/v1/admin/pricing/package-sizes`  
  Тело: `code`, `name_ru`, `name_uz`, `description` (опционально), `is_active`, `display_order`, `max_weight_kg`, `max_volume_m3` и т.п. (по схеме `PackageSizeCreate`).
- Список: `GET /api/v1/admin/pricing/package-sizes`.  
- Редактирование: `PUT /api/v1/admin/pricing/package-sizes/{size_id}`.  
- Удаление: `DELETE /api/v1/admin/pricing/package-sizes/{size_id}`.

**Шаг 2 — тарифы по регионам**

- **Создать тариф:**  
  `POST /api/v1/admin/pricing/tariffs`  
  Тело: `package_size_id`, `region_id` (или без региона — общий тариф), `base_price`, `currency`, `service_fee_percent`, `service_fee_fixed`, `min_price`, `max_price`, `is_active` (по схеме `PricingTariffCreate`).
- Список: `GET /api/v1/admin/pricing/tariffs` (фильтры: `region_id`, `package_size_id`, `is_active`).  
- Редактирование: `PUT /api/v1/admin/pricing/tariffs/{tariff_id}`.  
- Удаление: `DELETE /api/v1/admin/pricing/tariffs/{tariff_id}`.

**Что заполнить для экрана «от 4500 сум»:**  
Минимум один активный размер посылки и хотя бы один активный тариф (с `region_id` или без). Цена из тарифа (`base_price`) будет использоваться в расчёте и может отображаться как «от N сум».

---

### 1.3 Текстовый контент экрана (карточка, кнопка, сервисный сбор)

Сейчас тексты заданы **в коде** в `app/api/v1/regions.py` (константа `DELIVERY_SCREEN_CONTENT`):

- `card_title` — «По регионам Узбекистана»
- `delivery_time` — «1-3 дня»
- `price_from_label` — «от 4500 сум»
- `service_fee_text` — «В стоимость включен сервисный сбор в размере 0% (вместо 3%) от суммы заказа»
- `button_label` — «Перейти к форме заказа»

**Как изменить:** править эти значения в `app/api/v1/regions.py` и перезапустить сервер.  
Чтобы редактировать из админки, нужен отдельный API (например, `GET/PUT /api/v1/admin/regions/delivery-screen-content`) и раздел в админ-интерфейсе.

---

## 2. Мобильное приложение (какие запросы делать)

Базовый URL API: `https://<ваш-хост>/api/v1` (или без префикса, если он уже в базовом URL).

### 2.1 При открытии экрана «По регионам Узбекистана»

1. **Тексты карточки и кнопки**  
   `GET /api/v1/regions/delivery-screen-content`  
   Ответ: `card_title`, `delivery_time`, `price_from_label`, `service_fee_text`, `button_label`.  
   Подставлять эти строки в UI (заголовок, срок, «от N сум», текст про сервисный сбор, текст кнопки).

2. **Список регионов (для карты/выбора)**  
   `GET /api/v1/regions`  
   Опционально: `?is_active=true`.  
   Ответ: массив регионов с `id`, `name_ru`, `name_uz`, `center_latitude`, `center_longitude`, `display_order` и т.д.

3. **Цены по регионам (для блока «от 4500 сум»)**  
   `GET /api/v1/pricing/package-sizes/with-prices?region_id=<id>`  
   Если регион уже выбран — передать его `id`. Без `region_id` вернутся общие тарифы.  
   По ответу можно взять минимальную цену и сформировать строку вида «от 4500 сум» (или использовать `price_from_label` с бэкенда и при необходимости подставлять число).

### 2.2 Детали региона

- `GET /api/v1/regions/{region_id}` — данные одного региона (например, при выборе на карте).

### 2.3 Переход к форме заказа / расчёт стоимости

- **Расчёт цены:**  
  `POST /api/v1/pricing/calculate`  
  Тело по схеме `PriceCalculationRequest`: размер посылки, регион (если есть), параметры сервисного сбора и т.д.  
  Ответ: итоговая цена, разбивка (базовая цена, сервисный сбор) — использовать в форме заказа.

Дальнейшее создание заказа (если будет реализовано) — отдельный эндпоинт с токеном пользователя.

### 2.4 Авторизация

- Без токена: `GET /regions`, `GET /regions/delivery-screen-content`, `GET /regions/{id}`, `GET /pricing/package-sizes`, `GET /pricing/package-sizes/with-prices`.
- С токеном пользователя/админа: `POST /pricing/calculate` (если по логике нужна авторизация), админ-эндпоинты — только с токеном админа.

---

## Кратко

| Кто | Действие |
|-----|----------|
| **Админка** | Регионы — скрипт или БД; тарифы и размеры посылок — раздел «Админ: Тарифы и цены»; тексты экрана — пока в коде `regions.py`. |
| **Мобильное приложение** | При открытии экрана: запросить `delivery-screen-content` и `regions`, при необходимости `package-sizes/with-prices`; для формы заказа — `POST /pricing/calculate`. |
