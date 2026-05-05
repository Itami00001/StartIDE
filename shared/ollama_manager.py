import requests
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

class OllamaManager:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.base_url = base_url
        self.model = model
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
    def test_connection(self) -> bool:
        """Проверка подключения к Ollama"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Ollama: {e}")
            return False
    
    def send_project_context(self, project_path: str, context_data: Dict) -> bool:
        """Отправка контекста проекта в нейросеть через .txt файл"""
        try:
            # Создаем текстовый формат для нейросети
            context_text = self._format_context_for_ai(context_data, project_path)
            
            # Сохраняем во временный .txt файл
            temp_file = Path(project_path) / ".ai_context.txt"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(context_text)
            
            # Отправляем в Ollama
            response = self.session.post(f"{self.base_url}/api/generate", 
                json={
                    "model": self.model,
                    "prompt": f"Изучи контекст проекта:\n\n{context_text}\n\nГотов к вопросам о проекте.",
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                self.logger.info("Контекст проекта успешно отправлен в нейросеть")
                return True
            else:
                self.logger.error(f"Ошибка отправки контекста: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка при отправке контекста: {e}")
            return False
    
    def ask_about_project(self, question: str, project_path: str) -> Optional[str]:
        """Задать вопрос о проекте нейросети"""
        try:
            # Читаем контекст из .txt файла
            context_file = Path(project_path) / ".ai_context.txt"
            context_text = ""
            if context_file.exists():
                with open(context_file, 'r', encoding='utf-8') as f:
                    context_text = f.read()
            
            prompt = f"Контекст проекта:\n{context_text}\n\nВопрос: {question}"
            
            response = self.session.post(f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                return response.json().get('response', 'Нет ответа')
            else:
                return f"Ошибка: {response.status_code}"
                
        except Exception as e:
            self.logger.error(f"Ошибка при вопросе к нейросети: {e}")
            return f"Ошибка: {e}"
    
    def _format_context_for_ai(self, context_data: Dict, project_path: str) -> str:
        """Форматирует контекст в читаемый текстовый формат для нейросети"""
        formatted_text = []
        
        # Заголовок проекта
        project_name = Path(project_path).name
        formatted_text.append(f"=== ПРОЕКТ: {project_name} ===")
        formatted_text.append(f"Путь: {project_path}")
        formatted_text.append("")
        
        # Структура файлов
        if 'file_structure' in context_data:
            formatted_text.append("=== СТРУКТУРА ПРОЕКТА ===")
            self._format_file_structure(context_data['file_structure'], formatted_text, "")
            formatted_text.append("")
        
        # Код snippets
        if 'code_snippets' in context_data:
            formatted_text.append("=== ФРАГМЕНТЫ КОДА ===")
            for file_path, code in context_data['code_snippets'].items():
                formatted_text.append(f"Файл: {file_path}")
                formatted_text.append("-" * 50)
                formatted_text.append(code[:500] + "..." if len(code) > 500 else code)
                formatted_text.append("")
        
        # История контекста
        if 'context_history' in context_data:
            formatted_text.append("=== ИСТОРИЯ ИЗМЕНЕНИЙ ===")
            for entry in context_data['context_history'][-5:]:  # Последние 5 записей
                formatted_text.append(f"- {entry}")
            formatted_text.append("")
        
        return "\n".join(formatted_text)
    
    def _format_file_structure(self, structure: Dict, output: List[str], indent: str = ""):
        """Рекурсивно форматирует структуру файлов"""
        if 'folders' in structure:
            for folder in structure['folders']:
                output.append(f"{indent}📁 {folder['name']}/")
                self._format_file_structure(folder, output, indent + "  ")
        
        if 'files' in structure:
            for file in structure['files']:
                output.append(f"{indent}📄 {file['name']}")
