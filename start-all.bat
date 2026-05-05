@echo off
chcp 65001 >nul
echo ========================================
echo  START-beta - Полный запуск
echo ========================================
echo.
echo 📋 Этот скрипт запустит:
echo    1. MongoDB в Docker
echo    2. Проверку локальной Ollama
echo.
echo ========================================
echo.

:: Шаг 1: MongoDB
call start-mongodb.bat
if errorlevel 1 (
    echo ❌ Ошибка запуска MongoDB
    pause
    exit /b 1
)

echo.
echo ========================================
echo.

:: Шаг 2: Проверка Ollama
call check-ollama.bat
if errorlevel 1 (
    echo ❌ Ollama не готова
    pause
    exit /b 1
)

echo.
echo ========================================
echo  ✅ Все сервисы готовы!
echo ========================================
echo.
echo 🚀 Запуск приложений:
echo    python StartIDE\main.py
echo    python StartOffice\main.py
echo.

set /p START_IDE="Запустить StartIDE сейчас? (y/n): "
if /i "%START_IDE%"=="y" (
    start python StartIDE\main.py
)

set /p START_OFFICE="Запустить StartOffice сейчас? (y/n): "
if /i "%START_OFFICE%"=="y" (
    start python StartOffice\main.py
)

echo.
echo ========================================
echo  ✨ Готово к работе!
echo ========================================
echo.
echo 📊 Открытые сервисы:
echo    • Mongo Express: http://localhost:8081
echo    • Ollama API:    http://localhost:11434
echo.

pause
