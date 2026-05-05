# 🐳 Docker Setup для START-beta

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   MongoDB    │  │   Ollama     │  │Mongo Express │     │
│  │   :27017     │  │   :11434     │  │   :8081      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
         ▲                  ▲                  ▲
         │                  │                  │
    ┌────┴────┐      ┌────┴────┐      ┌──────┴──────┐
    │StartIDE │      │StartOffice│     │   Browser   │
    │ (native)│      │ (native) │      │  (localhost) │
    └─────────┘      └──────────┘      └──────────────┘
```

## 🚀 Быстрый старт

### 1. Установка Docker

Скачайте и установите [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 2. Запуск сервисов

```bash
# Windows (двойной клик)
start-docker.bat

# Или вручную:
docker-compose up -d
```

### 3. Проверка работы

```bash
# Проверка MongoDB
curl http://localhost:27017

# Проверка Ollama
curl http://localhost:11434/api/tags

# Веб-интерфейс MongoDB
# Откройте http://localhost:8081
# Логин: user / Пароль: pass
```

### 4. Запуск приложений

```bash
# В разных терминалах:
python StartIDE\main.py
python StartOffice\main.py
```

## 📦 Структура Docker

### MongoDB
- **Порт:** 27017
- **База данных:** start_beta
- **Пользователь:** start_app / app_password
- **Админ:** admin / password123
- **Веб-интерфейс:** http://localhost:8081

### Ollama
- **Порт:** 11434
- **Хранилище моделей:** ollama_data volume
- **GPU:** Поддерживается (см. docker-compose.yml)

## 🗄️ Схема данных MongoDB

### Коллекции:

1. **projects** - Проекты
   - Метаданные проекта
   - Настройки обработки файлов
   - Дерево файлов

2. **file_contents** - Содержимое файлов
   - Код с обрезкой по лимиту строк
   - Хеш для отслеживания изменений
   - Язык программирования

3. **ai_contexts** - Контекст AI (раздвижное окно 5)
   - Последние 5 сообщений
   - Авто-удаление старых
   - Перенумерация позиций

4. **full_conversations** - Полная история
   - Все диалоги без удаления
   - Сессии
   - Временные метки

5. **ai_responses_cache** - Кэш ответов
   - Авто-удаление через 24 часа
   - Уникальность по хешу запроса

## ⚙️ Настройка

### Переменные окружения

Создайте файл `.env` (скопируйте из `.env.example`):

```env
MONGODB_URI=mongodb://start_app:app_password@localhost:27017/start_beta
OLLAMA_BASE_URL=http://localhost:11434
MAX_CONTEXT_LINES=50
CONTEXT_WINDOW_SIZE=5
```

### Настройка обработки файлов

В MongoDB хранятся настройки каждого проекта:

```javascript
// Пример настроек проекта
{
  max_context_lines: 50,        // Сколько строк кода сохранять
  convert_to_txt: true,         // Конвертировать расширения
  file_extensions: [".py", ".js", ".html"]
}
```

## 🛠️ Управление Docker

### Основные команды

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f

# Очистка данных (осторожно!)
docker-compose down -v
```

### Управление MongoDB

```bash
# Вход в контейнер
docker exec -it start_mongodb mongosh -u admin -p password123 --authenticationDatabase admin

# Или внутри mongosh:
use start_beta
db.projects.find()
db.file_contents.countDocuments()
```

### Загрузка моделей Ollama

```bash
# Вход в контейнер Ollama
docker exec -it start_ollama ollama pull llama3.1
docker exec -it start_ollama ollama pull codellama
docker exec -it start_ollama ollama list
```

## 🔧 Устранение неполадок

### MongoDB не подключается

```bash
# Проверка статуса
docker-compose ps

# Перезапуск
docker-compose restart mongodb

# Просмотр ошибок
docker-compose logs mongodb
```

### Ollama не отвечает

```bash
# Проверка
curl http://localhost:11434/api/tags

# Перезапуск
docker-compose restart ollama
```

### Очистка и перезапуск

```bash
# Полная очистка (удалит все данные!)
docker-compose down -v
docker-compose up -d
```

## 💡 Режимы работы с файлами

### Режим 1: Конвертация в TXT (твоя идея)
```python
# В MongoDBManager.store_file_content()
# - Сохраняет код как текст
# - Обрезает по max_context_lines
# - Сохраняет метаданные (язык, размер)
```

### Режим 2: С указанием количества строк
```python
# Настройка per-project:
project.settings.max_context_lines = 100
# Или при сохранении конкретного файла:
store_file_content(..., max_lines=100)
```

## 📊 Мониторинг

### Mongo Express (веб-интерфейс)
- URL: http://localhost:8081
- Логин: user
- Пароль: pass

### Проверка статистики
```python
from shared import MongoDBManager

with MongoDBManager() as db:
    stats = db.health_check()
    print(stats)
    # {
    #   'status': 'connected',
    #   'projects': 5,
    #   'files': 127,
    #   'contexts': 5,
    #   'conversations': 23,
    #   'cached_responses': 45
    # }
```

## 🔒 Безопасность

- **Никогда не коммитьте `.env` файл**
- Смените пароли в production
- Используйте `docker-compose down -v` для очистки данных

## 🚀 Готовы к работе!

После запуска Docker:
1. Откройте http://localhost:8081 для просмотра базы данных
2. Запустите `python StartIDE\main.py`
3. Запустите `python StartOffice\main.py`
4. Создайте проект - он автоматически сохранится в MongoDB
