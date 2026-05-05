@echo off
chcp 65001 >nul
echo ========================================
echo  START-beta Docker Launcher
echo ========================================
echo.

:: Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker не найден. Установите Docker Desktop.
    pause
    exit /b 1
)

echo ✅ Docker найден

:: Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  docker-compose не найден, пробуем 'docker compose'...
    set COMPOSE_CMD=docker compose
) else (
    set COMPOSE_CMD=docker-compose
)

:: Copy .env if not exists
if not exist .env (
    echo 📋 Создание .env файла из примера...
    copy .env.example .env >nul
    echo ✅ .env создан. Отредактируйте при необходимости.
)

echo.
echo 🚀 Запуск сервисов (MongoDB + Ollama)...
echo ========================================

%COMPOSE_CMD% up -d

if errorlevel 1 (
    echo ❌ Ошибка запуска Docker сервисов
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ Сервисы запущены!
echo ========================================
echo.
echo 📊 Доступные сервисы:
echo    • MongoDB:        localhost:27017
echo    • Mongo Express:  http://localhost:8081 (логин: user/pass)
echo    • Ollama API:     http://localhost:11434
echo.
echo 📋 Полезные команды:
echo    • Просмотр логов:    %COMPOSE_CMD% logs -f
echo    • Остановка:         %COMPOSE_CMD% down
echo    • Перезапуск:        %COMPOSE_CMD% restart
echo    • Очистка данных:    %COMPOSE_CMD% down -v
echo.
echo 💡 Теперь запустите приложения:
echo    python StartIDE\main.py
echo    python StartOffice\main.py
echo.

pause
