# Frontend Setup

## Установка и запуск

### 1. Установка зависимостей

```bash
cd frontend
npm install
```

### 2. Разработка

Запуск dev-сервера (с hot-reload):

```bash
npm run dev
```

Приложение будет доступно на `http://localhost:3000`

### 3. Сборка для продакшена

```bash
npm run build
```

Собранные файлы будут в папке `static/` (настроено в `vite.config.js`)

### 4. Структура проекта

```
frontend/
├── src/
│   ├── components/      # Переиспользуемые компоненты
│   │   ├── Layout.jsx   # Основной layout с навигацией
│   │   └── ProtectedRoute.jsx
│   ├── contexts/         # React Contexts
│   │   └── AuthContext.jsx
│   ├── pages/           # Страницы приложения
│   │   ├── Login.jsx
│   │   ├── admin/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── BotChats.jsx
│   │   │   └── Logs.jsx
│   │   └── user/
│   │       ├── Dashboard.jsx
│   │       ├── Objects.jsx
│   │       └── CreateObject.jsx
│   ├── utils/           # Утилиты
│   │   └── api.js       # Axios конфигурация
│   ├── App.jsx          # Главный компонент с роутингом
│   └── main.jsx         # Точка входа
├── index.html
├── package.json
└── vite.config.js
```

## Дизайн

Приложение использует минималистичный дизайн в стиле [luma.com](https://luma.com/):
- Чистый, современный интерфейс
- Mobile-first подход
- Минималистичная цветовая палитра
- Плавные переходы и анимации

## API Integration

Все запросы к API идут через `/system` префикс (настроено в `vite.config.js` proxy).

В продакшене Flask будет отдавать статику из папки `static/`.

## Роутинг

Приложение использует React Router:
- `/login` - страница входа
- `/admin/dashboard` - админский дашборд
- `/admin/dashboard/bot-chats` - управление чатами
- `/admin/dashboard/logs` - просмотр логов
- `/user/dashboard` - пользовательский дашборд
- `/user/dashboard/objects` - список объектов
- `/user/dashboard/objects/create` - создание объекта

