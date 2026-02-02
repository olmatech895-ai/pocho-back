# Инструкция по подключению админской части

Базовый URL: `{BASE_URL}/api/v1`

---

## 1. Первоначальная настройка

### 1.1. Создание первого администратора

Если в базе ещё **нет ни одного администратора**, создайте первого админа **без токена**:

```
POST /admin/create-admin
Content-Type: application/json

{
  "phone_number": "+998901234567"
}
```

**Ответ (201 Created):**
```json
{
  "message": "Администратор успешно создан",
  "phone_number": "+998901234567",
  "login": "admin_abc123xyz",
  "password": "Xy9#kL2mPq",
  "user": {
    "id": 1,
    "phone_number": "+998901234567",
    "fullname": null,
    "is_active": true,
    "is_admin": true,
    "is_blocked": false,
    "created_at": "2026-02-02T12:00:00Z"
  }
}
```

**Важно:** Логин и пароль генерируются автоматически. Пароль показывается **только один раз** — сохраните его!

### 1.2. Создание дополнительных администраторов

Если админы уже есть, требуется токен текущего админа:

```
POST /admin/create-admin
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "phone_number": "+998909876543"
}
```

---

## 2. Авторизация администратора

### 2.1. Вход (получение токена)

```
POST /auth/admin/login
Content-Type: application/json

{
  "login": "admin_abc123xyz",
  "password": "Xy9#kL2mPq"
}
```

**Ответ (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Ошибки:**
- `401` — Неверный логин или пароль
- `403` — Пользователь не является администратором / аккаунт заблокирован или деактивирован

### 2.2. Использование токена

Все админские эндпоинты требуют заголовок:

```
Authorization: Bearer <access_token>
```

### 2.3. Выход

```
POST /auth/admin/logout
Authorization: Bearer <admin_token>
```

---

## 3. Админские эндпоинты (основные)

| Раздел | Prefix | Описание |
|--------|--------|----------|
| Пользователи | `/admin` | Список пользователей, блокировка, назначение админа, профили |
| Статистика | `/admin/statistics` | Админская статистика |
| Заправки | `/admin/gas-stations` | CRUD, модерация заправок |
| Рестораны | `/admin/restaurants` | CRUD, модерация ресторанов |
| СТО | `/admin/service-stations` | CRUD, модерация СТО |
| Автомойки | `/admin/car-washes` | CRUD, модерация автомоек |
| Электрозаправки | `/admin/electric-stations` | CRUD, модерация электрозаправок |
| Реклама | `/admin/advertisements` | Управление рекламой |
| Водители | `/admin/drivers` | Управление водителями |
| Доставка | `/admin/delivery` | Тарифы, заказы, назначение водителей |

---

## 4. Примеры подключения

### JavaScript / Fetch

```javascript
const BASE_URL = 'https://your-api.com/api/v1';

// 1. Вход
async function adminLogin(login, password) {
  const res = await fetch(`${BASE_URL}/auth/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login, password })
  });
  if (!res.ok) throw new Error(await res.text());
  const { access_token } = await res.json();
  return access_token;
}

// 2. Запрос с токеном
async function getAdminUsers(token, skip = 0, limit = 100) {
  const res = await fetch(
    `${BASE_URL}/admin/users?skip=${skip}&limit=${limit}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Использование
const token = await adminLogin('admin_abc123', 'password');
const users = await getAdminUsers(token);
```

### cURL

```bash
# Вход
TOKEN=$(curl -s -X POST "https://your-api.com/api/v1/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"login":"admin_abc123","password":"your_password"}' \
  | jq -r '.access_token')

# Запрос списка пользователей
curl -X GET "https://your-api.com/api/v1/admin/users?skip=0&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

### Flutter / Dart

```dart
// Вход
Future<String> adminLogin(String login, String password) async {
  final res = await http.post(
    Uri.parse('$baseUrl/auth/admin/login'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'login': login, 'password': password}),
  );
  if (res.statusCode != 200) throw Exception(res.body);
  return jsonDecode(res.body)['access_token'];
}

// Запрос с токеном
Future<Map<String, dynamic>> getAdminUsers(String token) async {
  final res = await http.get(
    Uri.parse('$baseUrl/admin/users'),
    headers: {'Authorization': 'Bearer $token'},
  );
  if (res.statusCode != 200) throw Exception(res.body);
  return jsonDecode(res.body);
}
```

---

## 5. Настройки (.env)

Рекомендуемые переменные окружения:

```env
# База данных
DATABASE_URL=postgresql://user:password@localhost:5432/pocho_db

# JWT (обязательно сменить в продакшене!)
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=20160

# Base URL для ссылок на файлы
BASE_URL=http://localhost:8000

# CORS (для админ-панели)
CORS_ORIGINS=http://localhost:3000,https://admin.your-domain.com
```

---

## 6. Типичные сценарии

### Сценарий 1: Первый запуск проекта

1. Развернуть бэкенд, выполнить миграции БД
2. `POST /admin/create-admin` с `phone_number` (без токена)
3. Сохранить `login` и `password`
4. В админ-панели: форма входа по логину и паролю
5. При успешном входе сохранить `access_token` (localStorage / secure storage)
6. Добавлять заголовок `Authorization: Bearer <token>` ко всем запросам

### Сценарий 2: Интеграция с React/Vue админкой

1. Страница логина → `POST /auth/admin/login`
2. При успехе сохранить токен (например, в `sessionStorage`)
3. В axios/fetch interceptor добавлять `Authorization: Bearer ${token}` к каждому запросу
4. При 401 — редирект на страницу логина
5. При выходе — `POST /auth/admin/logout`, очистить токен

### Сценарий 3: Срок действия токена

Токен действует `ACCESS_TOKEN_EXPIRE_MINUTES` минут (по умолчанию 2 недели). При истечении — 401, нужен повторный вход.

---

## 7. Краткая справка по эндпоинтам

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/admin/login` | Вход (login, password) → token |
| POST | `/auth/admin/logout` | Выход (Bearer token) |
| POST | `/admin/create-admin` | Создать админа (phone_number) |
| GET | `/admin/users` | Список пользователей |
| POST | `/admin/user/admin` | Назначить/снять права админа |
| POST | `/admin/user/block` | Блокировка пользователя |
| GET | `/admin/delivery/orders` | Заказы доставки |
| POST | `/admin/delivery/orders/{id}/assign-driver` | Назначить водителя |
| GET | `/admin/gas-stations/` | Список заправок (все статусы) |
| PUT | `/admin/gas-stations/{id}` | Редактирование заправки |
| ... | ... | См. Swagger `/docs` |

Полный список эндпоинтов: откройте `{BASE_URL}/docs` (Swagger UI).
