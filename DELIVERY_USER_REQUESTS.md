# Инструкция по отправке запросов доставки от пользователя

## Базовые настройки

### Base URL
```
https://your-api-domain.com/api/v1
```

### Аутентификация
Все запросы требуют Bearer токен в заголовке:
```
Authorization: Bearer <access_token>
```

### Формат данных
- Content-Type: `application/json`
- Все координаты: `latitude` (-90 до 90), `longitude` (-180 до 180)
- Все суммы в сумах (UZS)
- Баланс: единый баланс пользователя из `users_extended.balance`

---

## 📋 Эндпоинты для пользователя

### 1. Расчёт стоимости доставки

**POST** `/delivery/calculate-price`

**Описание:** Рассчитывает стоимость доставки между двумя точками без создания заказа. Не требует списания баланса.

**Запрос:**
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

**Ответ (200 OK):**
```json
{
  "distance_km": 2.5,
  "delivery_cost": 4500.0,
  "min_total": 5000.0,
  "cost_per_km": 1000.0,
  "base_fixed": 2000.0
}
```

**Ошибки:**
- `503 Service Unavailable` - Нет активного тарифа доставки
- `400 Bad Request` - Некорректные координаты
- `500 Internal Server Error` - Ошибка сервера

**Пример запроса (cURL):**
```bash
curl -X POST "https://api.example.com/api/v1/delivery/calculate-price" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

**Пример запроса (JavaScript/Fetch):**
```javascript
const response = await fetch('https://api.example.com/api/v1/delivery/calculate-price', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    pickup: {
      latitude: 41.3111,
      longitude: 69.2797,
      address: "Ташкент, ул. Навои 1"
    },
    dropoff: {
      latitude: 41.3150,
      longitude: 69.2800,
      address: "Ташкент, ул. Амира Темура 15"
    }
  })
});

const data = await response.json();
console.log('Стоимость доставки:', data.delivery_cost);
```

---

### 2. Создание заказа доставки

**POST** `/delivery/orders`

**Описание:** Создаёт новый заказ доставки. Автоматически:
- Проверяет баланс пользователя
- Списывает средства с баланса (`users_extended.balance`)
- Создаёт запись в истории статусов
- Заказ создаётся в статусе `created` (ожидает назначения водителя администратором)

**Запрос:**
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

**Поля запроса:**
- `pickup` (обязательно) - точка отправления с координатами и адресом
- `dropoff` (обязательно) - точка назначения с координатами и адресом
- `parcel_description` (опционально) - описание посылки
- `parcel_estimated_value` (опционально) - примерная стоимость посылки (>= 0)

**Ответ (201 Created):**
```json
{
  "id": 123,
  "user_id": 8,
  "driver_id": null,
  "pickup_latitude": 41.3111,
  "pickup_longitude": 69.2797,
  "pickup_address": "Ташкент, ул. Навои 1",
  "dropoff_latitude": 41.3150,
  "dropoff_longitude": 69.2800,
  "dropoff_address": "Ташкент, ул. Амира Темура 15",
  "parcel_description": "Документы",
  "parcel_estimated_value": 100000,
  "delivery_cost": 4500.0,
  "status": "created",
  "canceled_at": null,
  "cancel_reason": null,
  "created_at": "2026-02-02T12:00:00Z",
  "updated_at": null,
  "driver_name": null,
  "driver_phone": null
}
```

**Ошибки:**
- `400 Bad Request` - Недостаточно средств на балансе / Некорректные данные
- `401 Unauthorized` - Не авторизован
- `503 Service Unavailable` - Нет активного тарифа

**Важно:**
- Перед созданием заказа рекомендуется проверить баланс через `/delivery/balance`
- Средства списываются сразу при создании заказа
- Водитель назначается администратором. После назначения `driver_id`, `driver_name` и `driver_phone` будут заполнены

**Пример запроса (cURL):**
```bash
curl -X POST "https://api.example.com/api/v1/delivery/orders" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

**Пример запроса (JavaScript/Fetch):**
```javascript
async function createOrder(pickup, dropoff, parcelDescription) {
  try {
    // 1. Проверяем баланс
    const balanceResponse = await fetch('https://api.example.com/api/v1/delivery/balance', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const balance = await balanceResponse.json();
    
    // 2. Рассчитываем стоимость
    const priceResponse = await fetch('https://api.example.com/api/v1/delivery/calculate-price', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ pickup, dropoff })
    });
    const price = await priceResponse.json();
    
    // 3. Проверяем достаточность баланса
    if (balance.balance < price.delivery_cost) {
      throw new Error(`Недостаточно средств. Требуется: ${price.delivery_cost}, доступно: ${balance.balance}`);
    }
    
    // 4. Создаём заказ
    const orderResponse = await fetch('https://api.example.com/api/v1/delivery/orders', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        pickup,
        dropoff,
        parcel_description: parcelDescription,
        parcel_estimated_value: 100000
      })
    });
    
    if (!orderResponse.ok) {
      const error = await orderResponse.json();
      throw new Error(error.detail || 'Ошибка создания заказа');
    }
    
    const order = await orderResponse.json();
    return order;
  } catch (error) {
    console.error('Ошибка создания заказа:', error);
    throw error;
  }
}
```

---

### 3. Список моих заказов

**GET** `/delivery/orders?skip=0&limit=50&status=created`

**Параметры запроса:**
- `skip` (int, default=0, min=0) - Пропустить записей (для пагинации)
- `limit` (int, default=50, min=1, max=100) - Количество записей
- `status` (string, optional) - Фильтр по статусу (см. статусы ниже)

**Ответ (200 OK):**
```json
{
  "items": [
    {
      "id": 123,
      "user_id": 8,
      "driver_id": 12,
      "pickup_latitude": 41.3111,
      "pickup_longitude": 69.2797,
      "pickup_address": "Ташкент, ул. Навои 1",
      "dropoff_latitude": 41.3150,
      "dropoff_longitude": 69.2800,
      "dropoff_address": "Ташкент, ул. Амира Темура 15",
      "parcel_description": "Документы",
      "parcel_estimated_value": 100000,
      "delivery_cost": 4500.0,
      "status": "driver_assigned",
      "canceled_at": null,
      "cancel_reason": null,
      "created_at": "2026-02-02T12:00:00Z",
      "updated_at": "2026-02-02T12:05:00Z",
      "driver_name": "Иван Иванов",
      "driver_phone": "+998901234567"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

**Пример запроса (cURL):**
```bash
# Все заказы
curl -X GET "https://api.example.com/api/v1/delivery/orders?skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Только активные заказы
curl -X GET "https://api.example.com/api/v1/delivery/orders?status=driver_assigned&skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Пример запроса (JavaScript/Fetch):**
```javascript
async function getMyOrders(skip = 0, limit = 50, status = null) {
  const params = new URLSearchParams({
    skip: skip.toString(),
    limit: limit.toString()
  });
  
  if (status) {
    params.append('status', status);
  }
  
  const response = await fetch(
    `https://api.example.com/api/v1/delivery/orders?${params}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  return await response.json();
}

// Получить активные заказы
const activeOrders = await getMyOrders(0, 50, 'driver_assigned');

// Получить завершённые заказы
const completedOrders = await getMyOrders(0, 50, 'completed');
```

---

### 4. Получить заказ по ID

**GET** `/delivery/orders/{order_id}`

**Описание:** Получает детальную информацию о конкретном заказе. Можно получить только свои заказы.

**Ответ (200 OK):** Аналогичен объекту заказа из списка

**Ошибки:**
- `404 Not Found` - Заказ не найден или не принадлежит пользователю
- `401 Unauthorized` - Не авторизован

**Пример запроса (cURL):**
```bash
curl -X GET "https://api.example.com/api/v1/delivery/orders/123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Пример запроса (JavaScript/Fetch):**
```javascript
async function getOrder(orderId) {
  const response = await fetch(
    `https://api.example.com/api/v1/delivery/orders/${orderId}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  if (!response.ok) {
    throw new Error('Заказ не найден');
  }
  
  return await response.json();
}
```

---

### 5. Отмена заказа

**POST** `/delivery/orders/{order_id}/cancel`

**Описание:** Отменяет заказ пользователем. Возможна только до получения посылки водителем (до статуса `picked_up`). При отмене средства автоматически возвращаются на баланс.

**Запрос (опционально):**
```json
{
  "reason": "Передумал"
}
```

**Ответ (200 OK):** Обновлённый объект заказа со статусом `canceled`

**Ошибки:**
- `400 Bad Request` - Нельзя отменить (после получения посылки водителем)
- `404 Not Found` - Заказ не найден
- `401 Unauthorized` - Не авторизован

**Важно:**
- Отмена возможна только до статуса `picked_up`
- После статуса `picked_up`, `in_delivery`, `delivered`, `completed` отмена невозможна
- Средства возвращаются на баланс автоматически
- Причина отмены сохраняется в `cancel_reason`

**Пример запроса (cURL):**
```bash
curl -X POST "https://api.example.com/api/v1/delivery/orders/123/cancel" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Передумал"
  }'
```

**Пример запроса (JavaScript/Fetch):**
```javascript
async function cancelOrder(orderId, reason = null) {
  const response = await fetch(
    `https://api.example.com/api/v1/delivery/orders/${orderId}/cancel`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ reason })
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Нельзя отменить заказ');
  }
  
  return await response.json();
}

// Отмена с причиной
await cancelOrder(123, "Передумал");

// Отмена без причины
await cancelOrder(123);
```

---

### 6. Баланс пользователя

**GET** `/delivery/balance`

**Описание:** Получает текущий баланс пользователя. Это единый баланс из `users_extended.balance`, используемый для всех операций в системе.

**Ответ (200 OK):**
```json
{
  "balance": 50000.0
}
```

**Пример запроса (cURL):**
```bash
curl -X GET "https://api.example.com/api/v1/delivery/balance" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Пример запроса (JavaScript/Fetch):**
```javascript
async function getBalance() {
  const response = await fetch(
    'https://api.example.com/api/v1/delivery/balance',
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  const data = await response.json();
  return data.balance;
}

const balance = await getBalance();
console.log(`Текущий баланс: ${balance} сум`);
```

---

### 7. История движений по балансу

**GET** `/delivery/balance/log?skip=0&limit=50`

**Описание:** Получает историю всех операций с балансом пользователя (списания, возвраты).

**Параметры запроса:**
- `skip` (int, default=0, min=0) - Пропустить записей
- `limit` (int, default=50, min=1, max=100) - Количество записей

**Ответ (200 OK):**
```json
[
  {
    "id": 1,
    "order_id": 123,
    "amount": -4500.0,
    "type": "order_payment",
    "description": "Оплата заказа доставки",
    "created_at": "2026-02-02T12:00:00Z"
  },
  {
    "id": 2,
    "order_id": 123,
    "amount": 4500.0,
    "type": "refund",
    "description": "Возврат за отменённый заказ #123",
    "created_at": "2026-02-02T12:05:00Z"
  }
]
```

**Типы операций:**
- `order_payment` - Списание за заказ (amount < 0, отрицательное значение)
- `refund` - Возврат средств (amount > 0, положительное значение)
- `admin_adjustment` - Корректировка администратором

**Пример запроса (cURL):**
```bash
curl -X GET "https://api.example.com/api/v1/delivery/balance/log?skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Пример запроса (JavaScript/Fetch):**
```javascript
async function getBalanceLog(skip = 0, limit = 50) {
  const params = new URLSearchParams({
    skip: skip.toString(),
    limit: limit.toString()
  });
  
  const response = await fetch(
    `https://api.example.com/api/v1/delivery/balance/log?${params}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  return await response.json();
}

const log = await getBalanceLog();
log.forEach(entry => {
  const sign = entry.amount > 0 ? '+' : '';
  console.log(`${entry.created_at}: ${sign}${entry.amount} сум - ${entry.description}`);
});
```

---

## 📊 Статусы заказа

### Жизненный цикл заказа:

```
created → driver_assigned → driver_on_way → 
picked_up → in_delivery → delivered → completed
```

**Или отмена:**
```
... → canceled
```

### Описание статусов:

| Статус | Описание | Когда видит пользователь |
|--------|----------|--------------------------|
| `created` | Заказ создан, ожидает назначения водителя администратором | Сразу после создания |
| `driver_assigned` | Водитель назначен | После назначения администратором |
| `driver_on_way` | Водитель едет к точке забора | Водитель обновил статус |
| `picked_up` | Посылка получена водителем | Водитель забрал посылки |
| `in_delivery` | Посылка в доставке | Водитель едет к точке назначения |
| `delivered` | Посылка доставлена | Водитель доставил посылки |
| `completed` | Заказ завершён | Автоматически после `delivered` |
| `canceled` | Заказ отменён | После отмены пользователем или админом |

**Важно:** Отмена возможна только до статуса `picked_up`.

---

## 🔄 Рекомендации по работе с API

### 1. Проверка баланса перед созданием заказа

```javascript
async function createOrderWithBalanceCheck(pickup, dropoff) {
  // 1. Получаем баланс
  const balance = await getBalance();
  
  // 2. Рассчитываем стоимость
  const price = await calculatePrice(pickup, dropoff);
  
  // 3. Проверяем достаточность
  if (balance < price.delivery_cost) {
    const needed = price.delivery_cost - balance;
    throw new Error(`Недостаточно средств. Требуется пополнить на ${needed} сум`);
  }
  
  // 4. Создаём заказ
  return await createOrder(pickup, dropoff);
}
```

### 2. Отслеживание статуса заказа

```javascript
async function trackOrder(orderId, onStatusChange) {
  const interval = setInterval(async () => {
    try {
      const order = await getOrder(orderId);
      
      // Вызываем callback при изменении статуса
      onStatusChange(order);
      
      // Останавливаем отслеживание при завершении
      if (order.status === 'completed' || order.status === 'canceled') {
        clearInterval(interval);
      }
    } catch (error) {
      console.error('Ошибка отслеживания:', error);
      clearInterval(interval);
    }
  }, 5000); // Каждые 5 секунд
  
  return interval; // Для возможности остановки
}

// Использование
const tracking = trackOrder(123, (order) => {
  console.log('Статус заказа:', order.status);
  if (order.driver_name) {
    console.log('Водитель:', order.driver_name, order.driver_phone);
  }
});

// Остановить отслеживание
// clearInterval(tracking);
```

### 3. Обработка ошибок

```javascript
async function handleApiError(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Неизвестная ошибка' }));
    
    switch (response.status) {
      case 400:
        throw new Error(`Ошибка запроса: ${error.detail}`);
      case 401:
        // Перенаправить на экран авторизации
        throw new Error('Требуется авторизация');
      case 404:
        throw new Error('Не найдено');
      case 503:
        throw new Error('Сервис временно недоступен. Попробуйте позже.');
      default:
        throw new Error(error.detail || 'Ошибка сервера');
    }
  }
  
  return await response.json();
}
```

### 4. Полный пример создания заказа с обработкой ошибок

```javascript
async function createDeliveryOrder(pickup, dropoff, parcelDescription) {
  try {
    // 1. Проверка баланса
    const balanceResponse = await fetch('/api/v1/delivery/balance', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const balance = await handleApiError(balanceResponse);
    
    // 2. Расчёт стоимости
    const priceResponse = await fetch('/api/v1/delivery/calculate-price', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ pickup, dropoff })
    });
    const price = await handleApiError(priceResponse);
    
    // 3. Проверка достаточности баланса
    if (balance.balance < price.delivery_cost) {
      return {
        success: false,
        error: 'Недостаточно средств',
        required: price.delivery_cost,
        available: balance.balance,
        needToAdd: price.delivery_cost - balance.balance
      };
    }
    
    // 4. Создание заказа
    const orderResponse = await fetch('/api/v1/delivery/orders', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        pickup,
        dropoff,
        parcel_description: parcelDescription,
        parcel_estimated_value: 100000
      })
    });
    
    const order = await handleApiError(orderResponse);
    
    return {
      success: true,
      order: order,
      price: price
    };
    
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}
```

---

## ⚠️ Важные замечания

1. **Баланс:** Используется единый баланс из `users_extended.balance` для всех операций в системе
2. **Координаты:** Обязательно должны быть в диапазоне: latitude (-90 до 90), longitude (-180 до 180)
3. **Статусы:** Отслеживайте статусы заказа для обновления UI в реальном времени
4. **Отмена:** Возможна только до статуса `picked_up`
5. **Возврат средств:** Происходит автоматически при отмене заказа
6. **Водитель:** Информация о водителе появляется после статуса `driver_assigned`

---

## 📱 Примеры для мобильного приложения

### React Native / Expo

```javascript
import axios from 'axios';

const API_BASE_URL = 'https://api.example.com/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Добавление токена к запросам
apiClient.interceptors.request.use((config) => {
  const token = AsyncStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Расчёт стоимости
export const calculatePrice = async (pickup, dropoff) => {
  const response = await apiClient.post('/delivery/calculate-price', {
    pickup,
    dropoff
  });
  return response.data;
};

// Создание заказа
export const createOrder = async (orderData) => {
  const response = await apiClient.post('/delivery/orders', orderData);
  return response.data;
};

// Получение списка заказов
export const getMyOrders = async (skip = 0, limit = 50, status = null) => {
  const params = { skip, limit };
  if (status) params.status = status;
  
  const response = await apiClient.get('/delivery/orders', { params });
  return response.data;
};

// Отмена заказа
export const cancelOrder = async (orderId, reason = null) => {
  const response = await apiClient.post(`/delivery/orders/${orderId}/cancel`, {
    reason
  });
  return response.data;
};

// Получение баланса
export const getBalance = async () => {
  const response = await apiClient.get('/delivery/balance');
  return response.data.balance;
};
```

---

## 🔐 Безопасность

1. **Токены:** Храните токены в безопасном хранилище (Keychain/Keystore)
2. **HTTPS:** Всегда используйте HTTPS для API запросов
3. **Валидация:** Валидируйте данные на клиенте перед отправкой
4. **Ошибки:** Не показывайте технические детали ошибок пользователю

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи запросов
2. Убедитесь в корректности токена
3. Проверьте формат данных (особенно координаты)
4. Проверьте баланс перед созданием заказа
5. Обратитесь к администратору API
