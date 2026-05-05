@echo off
chcp 65001 >nul
echo ========================================
echo  Проверка локальной Ollama
echo ========================================
echo.

:: Проверка наличия команды ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Ollama НЕ установлен!
    echo.
    echo 📥 Установка Ollama:
    echo    1. Скачайте с https://ollama.com/download/windows
    echo    2. Установите и перезапустите терминал
    echo.
    pause
    exit /b 1
)

echo ✅ Ollama установлен
for /f "tokens=*" %%a in ('ollama --version') do (
    echo    Версия: %%a
)
echo.

:: Проверка запущен ли сервис
echo 🔍 Проверка сервиса Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Сервис Ollama НЕ запущен!
    echo.
    echo 🚀 Запуск Ollama:
    echo    ollama serve
    echo.
    echo Или запустите приложение Ollama из меню Пуск
    echo.
    pause
    exit /b 1
)

echo ✅ Сервис Ollama работает (порт 11434)
echo.

:: Проверка установленных моделей
echo 📦 Установленные модели:
echo ----------------------------------------
ollama list
echo.

:: Проверка наличия llama3.1
ollama list | findstr "llama3.1" >nul
if errorlevel 1 (
    echo ⚠️  Модель llama3.1 НЕ установлена!
    echo.
    echo 📥 Установка модели:
    echo    ollama pull llama3.1
    echo.
    set /p INSTALL="Установить сейчас? (y/n): "
    if /i "%INSTALL%"=="y" (
        echo.
        echo ⏳ Загрузка llama3.1...
        ollama pull llama3.1
        echo.
        echo ✅ Модель установлена!
    )
) else (
    echo ✅ Модель llama3.1 установлена
)

echo.
echo ========================================
echo  ✅ Ollama готова к работе!
echo ========================================
echo.
echo 📋 Доступные команды:
echo    ollama list          - список моделей
echo    ollama pull MODEL   - загрузить модель
echo    ollama serve         - запустить сервис
echo.

pause
