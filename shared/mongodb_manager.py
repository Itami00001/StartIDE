import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import DuplicateKeyError, ConnectionFailure
    from bson.objectid import ObjectId
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


class MongoDBManager:
    """Управление MongoDB для хранения проектов, файлов и AI контекста"""
    
    def __init__(self, connection_string: str = None):
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo не установлен. Установите: pip install pymongo")
        
        self.logger = logging.getLogger(__name__)
        
        # Получаем строку подключения из env или используем дефолтную
        self.connection_string = connection_string or os.getenv(
            'MONGODB_URI', 
            'mongodb://start_app:app_password@localhost:27017/start_beta'
        )
        
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Подключение к MongoDB"""
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client.start_beta
            
            # Проверка подключения
            self.client.admin.command('ping')
            self.logger.info("✅ Подключение к MongoDB успешно")
            
        except ConnectionFailure as e:
            self.logger.error(f"❌ Не удалось подключиться к MongoDB: {e}")
            raise
    
    # ==================== PROJECTS ====================
    
    def create_project(self, name: str, path: str, settings: Dict = None) -> str:
        """Создание нового проекта"""
        project_doc = {
            "name": name,
            "path": path,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "file_tree": {"folders": [], "files": []},
            "settings": settings or {
                "max_context_lines": int(os.getenv('MAX_CONTEXT_LINES', 50)),
                "convert_to_txt": True,
                "file_extensions": os.getenv('SUPPORTED_EXTENSIONS', '.py,.js,.html,.css,.md').split(',')
            }
        }
        
        try:
            result = self.db.projects.insert_one(project_doc)
            project_id = str(result.inserted_id)
            
            # Создаем пустой AI контекст для проекта
            self._create_empty_context(project_id)
            
            self.logger.info(f"✅ Проект создан: {name} (ID: {project_id})")
            return project_id
            
        except DuplicateKeyError:
            self.logger.warning(f"⚠️ Проект с именем '{name}' уже существует")
            # Возвращаем ID существующего проекта
            existing = self.db.projects.find_one({"name": name})
            return str(existing['_id'])
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """Получение проекта по ID"""
        return self.db.projects.find_one({"_id": ObjectId(project_id)})
    
    def update_project_file_tree(self, project_id: str, file_tree: Dict):
        """Обновление дерева файлов проекта"""
        self.db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {
                "$set": {
                    "file_tree": file_tree,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    def get_all_projects(self) -> List[Dict]:
        """Получение всех проектов"""
        return list(self.db.projects.find().sort("updated_at", DESCENDING))
    
    # ==================== FILE CONTENTS ====================
    
    def store_file_content(self, project_id: str, file_path: str, content: str, 
                          language: str = None, max_lines: int = None) -> str:
        """Сохранение содержимого файла"""
        
        # Получаем настройки проекта
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Проект {project_id} не найден")
        
        max_lines = max_lines or project['settings'].get('max_context_lines', 50)
        
        # Обрезаем контент по количеству строк
        lines = content.split('\n')
        if len(lines) > max_lines:
            content = '\n'.join(lines[:max_lines]) + f"\n... (обрезано, всего {len(lines)} строк)"
        
        # Определяем язык
        if not language:
            ext = Path(file_path).suffix.lower()
            language_map = {
                '.py': 'python', '.js': 'javascript', '.html': 'html',
                '.css': 'css', '.md': 'markdown', '.txt': 'text',
                '.json': 'json', '.xml': 'xml'
            }
            language = language_map.get(ext, 'unknown')
        
        file_doc = {
            "project_id": ObjectId(project_id),
            "file_path": file_path,
            "content": content,
            "language": language,
            "lines_count": len(lines),
            "hash": hashlib.sha256(content.encode()).hexdigest()[:16],
            "updated_at": datetime.utcnow()
        }
        
        # Upsert: обновить если существует, создать если нет
        result = self.db.file_contents.update_one(
            {"project_id": ObjectId(project_id), "file_path": file_path},
            {"$set": file_doc},
            upsert=True
        )
        
        self.logger.info(f"💾 Файл сохранен: {file_path} ({len(lines)} строк)")
        return str(result.upserted_id or 'updated')
    
    def get_file_content(self, project_id: str, file_path: str) -> Optional[str]:
        """Получение содержимого файла"""
        doc = self.db.file_contents.find_one({
            "project_id": ObjectId(project_id),
            "file_path": file_path
        })
        return doc['content'] if doc else None
    
    def get_project_files(self, project_id: str) -> List[Dict]:
        """Получение всех файлов проекта"""
        return list(self.db.file_contents.find(
            {"project_id": ObjectId(project_id)}
        ).sort("file_path", ASCENDING))
    
    def delete_file(self, project_id: str, file_path: str):
        """Удаление файла из БД"""
        self.db.file_contents.delete_one({
            "project_id": ObjectId(project_id),
            "file_path": file_path
        })
    
    # ==================== AI CONTEXT (5-window system) ====================
    
    def _create_empty_context(self, project_id: str):
        """Создание пустого контекста для проекта"""
        context_doc = {
            "project_id": ObjectId(project_id),
            "window_size": int(os.getenv('CONTEXT_WINDOW_SIZE', 5)),
            "messages": []
        }
        self.db.ai_contexts.insert_one(context_doc)
    
    def add_message_to_context(self, project_id: str, role: str, content: str) -> List[Dict]:
        """
        Добавление сообщения в контекст с раздвижным окном.
        Если превышает лимит - удаляет самое старое, сдвигает остальные.
        """
        window_size = int(os.getenv('CONTEXT_WINDOW_SIZE', 5))
        
        # Получаем текущий контекст
        context = self.db.ai_contexts.find_one({"project_id": ObjectId(project_id)})
        if not context:
            self._create_empty_context(project_id)
            context = {"messages": []}
        
        messages = context.get('messages', [])
        
        # Создаем новое сообщение
        new_message = {
            "role": role,  # "user" или "assistant"
            "content": content,
            "timestamp": datetime.utcnow()
        }
        
        # Логика раздвижного окна
        if len(messages) >= window_size:
            # Удаляем первое (самое старое)
            messages.pop(0)
        
        # Добавляем новое
        messages.append(new_message)
        
        # Перенумеровываем позиции
        for i, msg in enumerate(messages):
            msg['position'] = i + 1
        
        # Сохраняем в БД
        self.db.ai_contexts.update_one(
            {"project_id": ObjectId(project_id)},
            {"$set": {"messages": messages}}
        )
        
        self.logger.info(f"💬 Сообщение добавлено в контекст (всего: {len(messages)}/{window_size})")
        return messages
    
    def get_context(self, project_id: str) -> List[Dict]:
        """Получение текущего контекста проекта"""
        context = self.db.ai_contexts.find_one({"project_id": ObjectId(project_id)})
        return context.get('messages', []) if context else []
    
    def clear_context(self, project_id: str):
        """Очистка контекста проекта"""
        self.db.ai_contexts.update_one(
            {"project_id": ObjectId(project_id)},
            {"$set": {"messages": []}}
        )
    
    def get_context_for_prompt(self, project_id: str) -> str:
        """Получение контекста в текстовом формате для Ollama"""
        messages = self.get_context(project_id)
        if not messages:
            return "Нет предыдущего контекста."
        
        formatted = []
        for msg in messages:
            role = "Пользователь" if msg['role'] == 'user' else "Ассистент"
            formatted.append(f"[{role}]: {msg['content']}")
        
        return "\n".join(formatted)
    
    # ==================== FULL CONVERSATIONS ====================
    
    def save_full_conversation(self, project_id: str, session_id: str, messages: List[Dict]):
        """Сохранение полной истории диалога (не удаляется)"""
        conversation_doc = {
            "project_id": ObjectId(project_id),
            "session_id": session_id,
            "all_messages": messages,
            "created_at": datetime.utcnow()
        }
        
        self.db.full_conversations.update_one(
            {"project_id": ObjectId(project_id), "session_id": session_id},
            {"$set": conversation_doc},
            upsert=True
        )
    
    def get_conversation_history(self, project_id: str, session_id: str = None) -> List[Dict]:
        """Получение истории диалогов"""
        query = {"project_id": ObjectId(project_id)}
        if session_id:
            query["session_id"] = session_id
        
        return list(self.db.full_conversations.find(query).sort("created_at", DESCENDING))
    
    # ==================== AI CACHE ====================
    
    def get_cached_response(self, prompt: str) -> Optional[str]:
        """Получение кэшированного ответа AI"""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:32]
        
        cached = self.db.ai_responses_cache.find_one({"prompt_hash": prompt_hash})
        if cached:
            self.logger.info("🎯 Использован кэшированный ответ")
            return cached['response']
        return None
    
    def cache_response(self, prompt: str, response: str, model: str = "llama3.1"):
        """Кэширование ответа AI (авто-удаление через 24 часа)"""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:32]
        
        cache_doc = {
            "prompt_hash": prompt_hash,
            "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
            "response": response,
            "model": model,
            "created_at": datetime.utcnow()
        }
        
        self.db.ai_responses_cache.update_one(
            {"prompt_hash": prompt_hash},
            {"$set": cache_doc},
            upsert=True
        )
    
    # ==================== UTILITY ====================
    
    def close(self):
        """Закрытие соединения с MongoDB"""
        if self.client:
            self.client.close()
            self.logger.info("🔌 Соединение с MongoDB закрыто")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def health_check(self) -> Dict[str, Any]:
        """Проверка состояния БД"""
        try:
            self.client.admin.command('ping')
            stats = {
                "status": "connected",
                "projects": self.db.projects.count_documents({}),
                "files": self.db.file_contents.count_documents({}),
                "contexts": self.db.ai_contexts.count_documents({}),
                "conversations": self.db.full_conversations.count_documents({}),
                "cached_responses": self.db.ai_responses_cache.count_documents({})
            }
            return stats
        except Exception as e:
            return {"status": "error", "message": str(e)}
