import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import os

class AppLogger:
    """Разделенное логирование приложений (только системные логи)"""
    
    def __init__(self, context_path: str):
        self.context_path = Path(context_path)
        self.app_logs_file = self.context_path / "app_logs.txt"
        self.logger = logging.getLogger("AppLogger")
        
        # Создаем папку если не существует
        self.context_path.mkdir(exist_ok=True)
        
        # Настраиваем логирование
        self._setup_logging()
    
    def _setup_logging(self):
        """Настройка логирования в файл"""
        try:
            # Создаем handler для файла
            file_handler = logging.FileHandler(self.app_logs_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # Формат логов
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # Добавляем handler к логгеру
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)
            
            # Предотвращаем дублирование логов в консоль
            self.logger.propagate = False
            
        except Exception as e:
            print(f"Ошибка настройки логирования: {e}")
    
    def _write_log(self, level: str, action: str, details: str = "", app_name: str = "START-beta"):
        """Запись лога в файл"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Формируем строку лога
            if details:
                log_line = f"[{timestamp}] {level.upper()}: {action} - {details}"
            else:
                log_line = f"[{timestamp}] {level.upper()}: {action}"
            
            # Записываем в файл
            with open(self.app_logs_file, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
                f.flush()
            
            # Также логируем через Python logging
            log_method = getattr(self.logger, level.lower(), self.logger.info)
            log_method(f"{action} - {details}" if details else action)
            
        except Exception as e:
            print(f"Ошибка записи лога: {e}")
    
    def log_app_start(self, app_name: str):
        """Лог запуска приложения (только в app_logs.txt)"""
        self._write_log("info", f"APP_START", f"{app_name} запущена")
    
    def log_app_exit(self, app_name: str, reason: str = "normal"):
        """Лог закрытия приложения"""
        self._write_log("info", f"APP_EXIT", f"{app_name} закрыта (причина: {reason})")
    
    def log_project_open(self, project_path: str, project_id: Optional[int] = None):
        """Лог открытия проекта (только в app_logs.txt)"""
        project_name = Path(project_path).name
        details = f"{project_path}"
        if project_id:
            details += f" (ID: {project_id})"
        self._write_log("info", "PROJECT_OPEN", details)
    
    def log_project_close(self, project_path: str):
        """Лог закрытия проекта"""
        project_name = Path(project_path).name
        self._write_log("info", "PROJECT_CLOSE", f"{project_path}")
    
    def log_voice_action(self, action: str, details: str = ""):
        """Лог голосовых действий (только в app_logs.txt)"""
        if details:
            self._write_log("info", f"VOICE_{action.upper()}", details)
        else:
            self._write_log("info", f"VOICE_{action.upper()}")
    
    def log_git_action(self, action: str, details: str = ""):
        """Лог Git действий (только в app_logs.txt)"""
        if details:
            self._write_log("info", f"GIT_{action.upper()}", details)
        else:
            self._write_log("info", f"GIT_{action.upper()}")
    
    def log_database_action(self, action: str, details: str = ""):
        """Лог действий с базой данных"""
        if details:
            self._write_log("info", f"DB_{action.upper()}", details)
        else:
            self._write_log("info", f"DB_{action.upper()}")
    
    def log_file_action(self, action: str, file_path: str):
        """Лог действий с файлами"""
        self._write_log("info", f"FILE_{action.upper()}", file_path)
    
    def log_ai_interaction(self, request: str, success: bool, response_time: Optional[float] = None):
        """Лог взаимодействия с AI"""
        status = "SUCCESS" if success else "ERROR"
        details = f"Запрос: {request[:100]}... | Статус: {status}"
        if response_time:
            details += f" | Время: {response_time:.2f}s"
        self._write_log("info", "AI_INTERACTION", details)
    
    def log_error(self, error: str, context: str = ""):
        """Лог ошибок (только в app_logs.txt)"""
        if context:
            self._write_log("error", "ERROR", f"{context}: {error}")
        else:
            self._write_log("error", "ERROR", error)
    
    def log_warning(self, warning: str, context: str = ""):
        """Лог предупреждений"""
        if context:
            self._write_log("warning", "WARNING", f"{context}: {warning}")
        else:
            self._write_log("warning", "WARNING", warning)
    
    def log_ui_action(self, action: str, details: str = ""):
        """Лог действий пользователя в интерфейсе"""
        if details:
            self._write_log("info", f"UI_{action.upper()}", details)
        else:
            self._write_log("info", f"UI_{action.upper()}")
    
    def log_network_action(self, action: str, url: str, status_code: Optional[int] = None):
        """Лог сетевых действий"""
        details = f"URL: {url}"
        if status_code:
            details += f" | Код: {status_code}"
        self._write_log("info", f"NETWORK_{action.upper()}", details)
    
    def get_recent_logs(self, count: int = 50) -> list:
        """Получение последних логов"""
        try:
            if not self.app_logs_file.exists():
                return []
            
            with open(self.app_logs_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Возвращаем последние строки
            return [line.strip() for line in lines[-count:] if line.strip()]
            
        except Exception as e:
            self.logger.error(f"Ошибка чтения логов: {e}")
            return []
    
    def clear_logs(self):
        """Очистка логов"""
        try:
            with open(self.app_logs_file, 'w', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: LOGS_CLEARED\n")
            self._write_log("info", "LOGS_CLEARED", "Логи очищены пользователем")
        except Exception as e:
            self.logger.error(f"Ошибка очистки логов: {e}")
    
    def get_log_stats(self) -> dict:
        """Получение статистики по логам"""
        try:
            if not self.app_logs_file.exists():
                return {"total_lines": 0, "errors": 0, "warnings": 0}
            
            with open(self.app_logs_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            stats = {
                "total_lines": len(lines),
                "errors": 0,
                "warnings": 0,
                "info": 0,
                "last_log": ""
            }
            
            for line in lines:
                if "ERROR:" in line:
                    stats["errors"] += 1
                elif "WARNING:" in line:
                    stats["warnings"] += 1
                elif "INFO:" in line:
                    stats["info"] += 1
            
            if lines:
                stats["last_log"] = lines[-1].strip()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики логов: {e}")
            return {"total_lines": 0, "errors": 0, "warnings": 0}
    
    def export_logs(self, export_path: str, date_from: Optional[str] = None, date_to: Optional[str] = None):
        """Экспорт логов в файл"""
        try:
            if not self.app_logs_file.exists():
                raise FileNotFoundError("Файл логов не существует")
            
            with open(self.app_logs_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Фильтрация по датам если указаны
            filtered_lines = []
            if date_from or date_to:
                for line in lines:
                    try:
                        # Извлекаем дату из строки лога
                        date_str = line.split(']')[0][1:]  # Получаем дату между [ и ]
                        log_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        
                        # Проверяем диапазон дат
                        if date_from and log_date < datetime.strptime(date_from, '%Y-%m-%d'):
                            continue
                        if date_to and log_date > datetime.strptime(date_to, '%Y-%m-%d'):
                            continue
                        
                        filtered_lines.append(line)
                    except:
                        # Если не удалось распарсить дату, включаем строку
                        filtered_lines.append(line)
            else:
                filtered_lines = lines
            
            # Записываем в файл экспорта
            with open(export_path, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
            
            self._write_log("info", "LOGS_EXPORTED", f"Экспортировано {len(filtered_lines)} строк в {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта логов: {e}")
            return False


# Глобальный экземпляр для использования в приложениях
_global_app_logger = None

def get_app_logger(context_path: str = "context") -> AppLogger:
    """Получение глобального экземпляра логгера"""
    global _global_app_logger
    if _global_app_logger is None:
        _global_app_logger = AppLogger(context_path)
    return _global_app_logger

def init_app_logging(context_path: str = "context", app_name: str = "START-beta"):
    """Инициализация логирования приложения"""
    logger = get_app_logger(context_path)
    logger.log_app_start(app_name)
    return logger
