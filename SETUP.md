# 🚀 Настройка START-beta

## ⚡ Быстрый старт

```bash
# 1. Запустить MongoDB (Docker)
start-mongodb.bat

# 2. Проверить/запустить локальную Ollama
check-ollama.bat

# 3. Или всё сразу:
start-all.bat
```

## 📋 Что изменилось?

### ✅ Теперь используется:
| Сервис | Раньше | Сейчас | Почему |
|--------|--------|--------|--------|
| **MongoDB** | ❌ Не было | ✅ Docker | Нужна для хранения данных |
| **Ollama** | ✅ Docker (4GB+) | ✅ Локальная | Экономия RAM/CPU |

### 💡 Преимущества локальной Ollama:
- ✅ Не грузит оперативку повторно
- ✅ Использует уже скачанные модели
- ✅ Быстрее запускается
- ✅ Не нужно ждать загрузки 5GB в Docker

## 🗄️ Архитектура

```
┌─────────────────────────────────────┐
│         MongoDB (Docker)            │
│         localhost:27017             │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │projects │ │ files   │ │ contexts│ │
│  └─────────┘ └─────────┘ └────────┘ │
└─────────────────────────────────────┘
              ▲
              │ pymongo
┌─────────────┴─────────────┐
│   StartIDE / StartOffice  │
│      (Python/Tkinter)     │
└─────────────┬─────────────┘
              │ requests
┌─────────────┴─────────────┐
│   Ollama (Local)          │
│   localhost:11434         │
│   - llama3.1              │
│   - codellama             │
└───────────────────────────┘
```

## 🛠️ Установка

### 1. Установить Ollama (если еще нет)

**Windows:**
```bash
# Скачать с сайта и установить:
# https://ollama.com/download/windows

# Проверить установку:
ollama --version
```

### 2. Запустить MongoDB (Docker)

```bash
start-mongodb.bat
```

Или вручную:
```bash
docker-compose up -d
```

### 3. Загрузить модель Ollama

```bash
ollama pull llama3.1
```

### 4. Создать .env файл

```bash
copy .env.example .env
```

Файл `.env` уже настроен на локальную Ollama:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

### 5. Установить Python зависимости

```bash
pip install -r requirements.txt
```

### 6. Запустить приложения

```bash
python StartIDE\main.py
python StartOffice\main.py
```

## 🧪 Проверка работы

### Проверка MongoDB:
```bash
# Веб-интерфейс
http://localhost:8081
# Логин: user / Пароль: pass

# Python
python -c "from shared.mongodb_manager import MongoDBManager; db = MongoDBManager(); print(db.health_check())"
```

### Проверка Ollama:
```bash
# Список моделей
ollama list

# API
curl http://localhost:11434/api/tags
```

## 📊 Использование ресурсов

| Сервис | RAM | CPU | Диск |
|--------|-----|-----|------|
| MongoDB | ~300MB | Низкая | ~100MB |
| Ollama (1 модель) | ~4-8GB | Средняя | ~5GB |
| StartIDE | ~50MB | Низкая | - |
| StartOffice | ~50MB | Низкая | - |

**Итого с Docker Ollama:** ~8-12GB RAM  
**Итого с локальной Ollama:** ~4-8GB RAM (экономия 4GB!)

## 🔧 Управление

### MongoDB
```bash
# Запуск
start-mongodb.bat

# Остановка
docker-compose down

# Логи
docker-compose logs -f

# Полный сброс (удалит данные!)
docker-compose down -v
```

### Ollama
```bash
# Проверка
check-ollama.bat

# Список моделей
ollama list

# Загрузка модели
ollama pull llama3.1
ollama pull codellama

# Запуск сервиса (если не работает)
ollama serve

# Удаление модели
ollama rm llama3.1
```

## 🐛 Troubleshooting

### "Ollama не найдена"
```bash
# Установить Ollama
# https://ollama.com/download/windows

# Добавить в PATH если нужно
```

### "MongoDB не подключается"
```bash
# Проверить Docker
docker ps

# Перезапустить
docker-compose restart

# Проверить порт 27017
netstat -an | findstr 27017
```

### "Модель не найдена"
```bash
# Загрузить модель
ollama pull llama3.1

# Проверить список
ollama list
```

## 📁 Файлы

```
START-beta/
├── start-mongodb.bat       # Запуск MongoDB
├── check-ollama.bat        # Проверка Ollama
├── start-all.bat          # Полный запуск
├── docker-compose.yml     # Только MongoDB
├── .env.example          # Настройки (локальная Ollama)
├── SETUP.md              # Этот файл
└── ...
```

## ✅ Готово!

Теперь у тебя:
- ✅ MongoDB в Docker (данные проектов)
- ✅ Локальная Ollama (экономия 4GB RAM)
- ✅ Раздвижное окно из 5 сообщений
- ✅ Хранение кода с обрезкой по строкам
- ✅ Полная история диалогов
- ✅ Кэширование ответов AI

**Запуск:** `start-all.bat`
