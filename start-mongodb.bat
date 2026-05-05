@echo off
chcp 65001 >nul
echo ========================================
echo  START-beta - MongoDB Docker Launcher
echo ========================================
echo.

:: Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker не найден. Установите Docker Desktop.
    echo    https://www.docker.com/products/docker-desktop/
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
echo 🚀 Запуск MongoDB...
echo ========================================

%COMPOSE_CMD% up -d

if errorlevel 1 (
    echo ❌ Ошибка запуска Docker сервисов
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ MongoDB запущена!
echo ========================================
echo.
echo 📊 Доступные сервисы:
echo    • MongoDB:        localhost:27017
echo    • Mongo Express:  http://localhost:8081 (логин: user/pass)
echo.
echo 📋 Команды:
echo    • Логи:    %COMPOSE_CMD% logs -f
echo    • Стоп:    %COMPOSE_CMD% down
echo    • Статус:  docker ps
echo.
echo 💡 Следующий шаг: проверка Ollama
echo    check-ollama.bat
echo.

pause
