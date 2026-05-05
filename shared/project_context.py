from pathlib import Path
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime

class ProjectContext:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.context_file = self.project_path / ".project_context.json"
        self.logger = logging.getLogger(__name__)
        
    def get_project_structure(self) -> Dict:
        """Анализирует структуру проекта"""
        structure = {
            "folders": [],
            "files": []
        }
        
        try:
            for item in self.project_path.iterdir():
                if item.name.startswith('.'):
                    continue
                    
                if item.is_dir():
                    structure["folders"].append({
                        "name": item.name,
                        "path": str(item)
                    })
                elif item.is_file() and item.suffix in ['.txt', '.py', '.js', '.html', '.css', '.md']:
                    structure["files"].append({
                        "name": item.name,
                        "path": str(item),
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime
                    })
        except Exception as e:
            self.logger.error(f"Ошибка анализа структуры: {e}")
        
        return structure
    
    def extract_code_snippets(self, max_files: int = 10, max_size: int = 5000) -> Dict[str, str]:
        """Извлекает фрагменты кода из файлов проекта"""
        snippets = {}
        
        try:
            files_processed = 0
            for item in self.project_path.iterdir():
                if files_processed >= max_files:
                    break
                    
                if item.is_file() and not item.name.startswith('.'):
                    if item.suffix in ['.txt', '.py', '.js', '.html', '.css', '.md']:
                        try:
                            with open(item, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if len(content) <= max_size:
                                    snippets[str(item.relative_to(self.project_path))] = content
                                else:
                                    snippets[str(item.relative_to(self.project_path))] = content[:max_size] + "\n... (обрезано)"
                                files_processed += 1
                        except Exception as e:
                            self.logger.warning(f"Не удалось прочитать файл {item}: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка извлечения фрагментов: {e}")
        
        return snippets
    
    def update_context(self, action: str, details: str = ""):
        """Обновляет историю контекста"""
        try:
            context_data = self.load_context()
            
            # Добавляем запись в историю
            history_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "details": details
            }
            
            if "context_history" not in context_data:
                context_data["context_history"] = []
            
            context_data["context_history"].append(history_entry)
            
            # Ограничиваем историю последними 50 записями
            if len(context_data["context_history"]) > 50:
                context_data["context_history"] = context_data["context_history"][-50:]
            
            # Обновляем структуру проекта
            context_data["file_structure"] = self.get_project_structure()
            
            # Обновляем фрагменты кода
            context_data["code_snippets"] = self.extract_code_snippets()
            
            # Сохраняем контекст
            self.save_context(context_data)
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления контекста: {e}")
    
    def load_context(self) -> Dict:
        """Загружает контекст проекта"""
        try:
            if self.context_file.exists():
                with open(self.context_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "project_name": self.project_path.name,
                    "created": datetime.now().isoformat(),
                    "file_structure": self.get_project_structure(),
                    "code_snippets": self.extract_code_snippets(),
                    "context_history": []
                }
        except Exception as e:
            self.logger.error(f"Ошибка загрузки контекста: {e}")
            return {}
    
    def save_context(self, context_data: Dict):
        """Сохраняет контекст проекта"""
        try:
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения контекста: {e}")
    
    def add_file_change(self, file_path: str, change_type: str):
        """Добавляет информацию об изменении файла"""
        details = f"Файл: {file_path}, Действие: {change_type}"
        self.update_context("file_change", details)
    
    def add_folder_change(self, folder_path: str, change_type: str):
        """Добавляет информацию об изменении папки"""
        details = f"Папка: {folder_path}, Действие: {change_type}"
        self.update_context("folder_change", details)
