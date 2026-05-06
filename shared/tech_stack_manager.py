from pathlib import Path
from typing import Dict, List, Optional, Set
import json
import logging
from datetime import datetime
from .tech_stack_detector import TechStackDetector
from .git_manager import GitManager

class TechStackManager:
    def __init__(self, project_path: str, db_manager):
        self.project_path = Path(project_path)
        self.db_manager = db_manager
        self.project_id = None
        self.logger = logging.getLogger(__name__)
        
        # Инициализация детекторов
        self.tech_detector = TechStackDetector(str(project_path))
        self.git_manager = GitManager(str(project_path), db_manager)
    
    def analyze_and_save_tech_stack(self, project_id: int) -> Dict:
        """Полный анализ технологического стека"""
        try:
            self.project_id = project_id
            
            # 1. Автоопределение из файлов
            auto_detected = self.tech_detector.detect_tech_stack()
            
            # 2. Анализ из Git
            git_detected = self.git_manager.analyze_dependencies_from_git(project_id)
            
            # 3. Объединение результатов
            combined_stack = self._combine_detection_results(auto_detected, git_detected)
            
            # 4. Сохранение в базу данных
            self._save_tech_stack_to_db(project_id, combined_stack)
            
            # 5. Обновление tech_stack.txt файла
            self._update_tech_stack_file(project_id, combined_stack)
            
            self.logger.info(f"Технологический стек проанализирован для проекта {project_id}")
            return combined_stack
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа технологического стека: {e}")
            return {}
    
    def _combine_detection_results(self, auto_detected: Dict, git_detected: Dict) -> Dict:
        """Объединение результатов автоопределения и Git анализа"""
        combined = {
            'languages': [],
            'frameworks': [],
            'databases': [],
            'tools': [],
            'libraries': [],
            'package_managers': []
        }
        
        # Объединяем автоопределенные технологии
        for category in ['languages', 'frameworks', 'databases', 'tools', 'libraries']:
            if category in auto_detected:
                combined[category].extend(auto_detected[category])
        
        # Добавляем Git результаты
        if 'frameworks' in git_detected:
            combined['frameworks'].extend([
                {'name': fw, 'version': None, 'confidence': 0.8, 'detected_by': 'git_analysis'}
                for fw in git_detected['frameworks']
            ])
        
        if 'libraries' in git_detected:
            combined['libraries'].extend([
                {'name': lib, 'version': None, 'confidence': 0.8, 'detected_by': 'git_analysis'}
                for lib in git_detected['libraries']
            ])
        
        if 'dev_tools' in git_detected:
            combined['tools'].extend([
                {'name': tool, 'version': None, 'confidence': 0.8, 'detected_by': 'git_analysis'}
                for tool in git_detected['dev_tools']
            ])
        
        if 'package_managers' in git_detected:
            combined['package_managers'] = [
                {'name': pm, 'version': None, 'confidence': 0.9, 'detected_by': 'git_analysis'}
                for pm in git_detected['package_managers']
            ]
        
        # Удаление дубликатов и сортировка
        for category in combined:
            combined[category] = self._deduplicate_tech_items(combined[category])
        
        return combined
    
    def _deduplicate_tech_items(self, items: List[Dict]) -> List[Dict]:
        """Удаление дубликатов с сохранением максимальной уверенности"""
        seen = {}
        unique_items = []
        
        for item in items:
            name = item['name']
            if name not in seen or item['confidence'] > seen[name]['confidence']:
                seen[name] = item
        
        return sorted(seen.values(), key=lambda x: x['confidence'], reverse=True)
    
    def _save_tech_stack_to_db(self, project_id: int, tech_stack: Dict):
        """Сохранение технологического стека в базу данных"""
        try:
            # Очищаем старые записи для этого проекта
            self.db_manager.conn.execute(
                "DELETE FROM tech_stack WHERE project_id = ?",
                (project_id,)
            )
            
            # Сохраняем новые записи
            for category, items in tech_stack.items():
                for item in items:
                    self.db_manager.conn.execute(
                        """
                        INSERT INTO tech_stack 
                        (project_id, technology, version, detected_by, confidence)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            item['name'],
                            item.get('version'),
                            item.get('detected_by', 'auto'),
                            item.get('confidence', 0.5)
                        )
                    )
            
            self.db_manager.conn.commit()
            self.logger.info(f"Сохранен технологический стек в БД для проекта {project_id}")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения технологического стека в БД: {e}")
    
    def _update_tech_stack_file(self, project_id: int, tech_stack: Dict):
        """Обновление tech_stack.txt файла"""
        try:
            project_folder = self.db_manager.projects_dir / f"project_{project_id}"
            project_folder.mkdir(parents=True, exist_ok=True)
            
            content = []
            content.append("=== ТЕХНОЛОГИЧЕСКИЙ СТЕК ===")
            content.append(f"Проект: {self.project_path.name}")
            content.append(f"Обновлено: {datetime.now().isoformat()}")
            content.append("")
            
            # Основные технологии
            all_tech = []
            for category, items in tech_stack.items():
                if items and category != 'package_managers':
                    all_tech.extend([(item['name'], item.get('version'), item.get('confidence', 0.5)) for item in items])
            
            if all_tech:
                content.append("=== ОСНОВНЫЕ ТЕХНОЛОГИИ ===")
                # Сортируем по уверенности
                all_tech.sort(key=lambda x: x[2], reverse=True)
                for name, version, confidence in all_tech[:15]:  # Показываем топ-15
                    version_str = f" {version}" if version else ""
                    content.append(f"{name}{version_str}")
                content.append("")
            
            # Категории
            category_names = {
                'languages': 'ЯЗЫКИ ПРОГРАММИРОВАНИЯ',
                'frameworks': 'ФРЕЙМВОРКИ',
                'databases': 'БАЗЫ ДАННЫХ',
                'tools': 'ИНСТРУМЕНТЫ',
                'libraries': 'БИБЛИОТЕКИ',
                'package_managers': 'МЕНЕДЖЕРЫ ПАКЕТОВ'
            }
            
            for category, items in tech_stack.items():
                if items:
                    content.append(f"=== {category_names.get(category, category.upper())} ===")
                    for item in items:
                        version = item.get('version', '')
                        confidence = item.get('confidence', 0.5)
                        detected_by = item.get('detected_by', 'auto')
                        
                        version_str = f" {version}" if version else ""
                        confidence_str = f" ({confidence:.1f})" if confidence < 1.0 else ""
                        detected_str = f" - {detected_by}" if detected_by != 'auto' else ""
                        
                        content.append(f"{item['name']}{version_str}{confidence_str}{detected_str}")
                    content.append("")
            
            # Git версии (если есть)
            if self.git_manager.is_git_repo:
                tags = self.git_manager.get_tags()
                if tags:
                    content.append("=== GIT ВЕРСИИ ===")
                    for tag in tags[:10]:
                        success, commit_hash = self.git_manager._run_git_command(['rev-list', '-n', '1', tag])
                        if success:
                            success, commit_date = self.git_manager._run_git_command(
                                ['log', '-1', '--format=%ci', commit_hash]
                            )
                            if success:
                                content.append(f"{tag} - {commit_hash[:8]} ({commit_date})")
                    content.append("")
            
            with open(project_folder / "tech_stack.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления tech_stack.txt: {e}")
    
    def get_tech_stack_from_db(self, project_id: int) -> List[Dict]:
        """Получение технологического стека из базы данных"""
        try:
            cursor = self.db_manager.conn.execute(
                """
                SELECT technology, version, detected_by, confidence, created
                FROM tech_stack 
                WHERE project_id = ? 
                ORDER BY confidence DESC, created DESC
                """,
                (project_id,)
            )
            
            tech_stack = []
            for row in cursor.fetchall():
                tech_stack.append({
                    'name': row[0],
                    'version': row[1],
                    'detected_by': row[2],
                    'confidence': row[3],
                    'created': row[4]
                })
            
            return tech_stack
            
        except Exception as e:
            self.logger.error(f"Ошибка получения технологического стека из БД: {e}")
            return []
    
    def add_manual_tech_item(self, project_id: int, technology: str, version: str = None) -> bool:
        """Ручное добавление технологии"""
        try:
            # Проверяем, существует ли уже
            cursor = self.db_manager.conn.execute(
                "SELECT id FROM tech_stack WHERE project_id = ? AND technology = ?",
                (project_id, technology)
            )
            
            if cursor.fetchone():
                # Обновляем существующую запись
                self.db_manager.conn.execute(
                    """
                    UPDATE tech_stack 
                    SET version = ?, detected_by = 'manual', confidence = 1.0
                    WHERE project_id = ? AND technology = ?
                    """,
                    (version, project_id, technology)
                )
            else:
                # Добавляем новую запись
                self.db_manager.conn.execute(
                    """
                    INSERT INTO tech_stack (project_id, technology, version, detected_by, confidence)
                    VALUES (?, ?, ?, 'manual', 1.0)
                    """,
                    (project_id, technology, version)
                )
            
            self.db_manager.conn.commit()
            
            # Обновляем файл
            tech_stack = self.get_tech_stack_from_db(project_id)
            self._update_tech_stack_file(project_id, self._convert_db_to_dict(tech_stack))
            
            self.logger.info(f"Добавлена технология вручную: {technology}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления технологии вручную: {e}")
            return False
    
    def remove_tech_item(self, project_id: int, technology: str) -> bool:
        """Удаление технологии"""
        try:
            self.db_manager.conn.execute(
                "DELETE FROM tech_stack WHERE project_id = ? AND technology = ?",
                (project_id, technology)
            )
            self.db_manager.conn.commit()
            
            # Обновляем файл
            tech_stack = self.get_tech_stack_from_db(project_id)
            self._update_tech_stack_file(project_id, self._convert_db_to_dict(tech_stack))
            
            self.logger.info(f"Удалена технология: {technology}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка удаления технологии: {e}")
            return False
    
    def update_tech_item(self, project_id: int, technology: str, version: str = None) -> bool:
        """Обновление версии технологии"""
        try:
            self.db_manager.conn.execute(
                """
                UPDATE tech_stack 
                SET version = ?, detected_by = 'manual', confidence = 1.0
                WHERE project_id = ? AND technology = ?
                """,
                (version, project_id, technology)
            )
            self.db_manager.conn.commit()
            
            # Обновляем файл
            tech_stack = self.get_tech_stack_from_db(project_id)
            self._update_tech_stack_file(project_id, self._convert_db_to_dict(tech_stack))
            
            self.logger.info(f"Обновлена технология: {technology} -> {version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления технологии: {e}")
            return False
    
    def _convert_db_to_dict(self, tech_stack: List[Dict]) -> Dict:
        """Конвертация формата из БД в словарь для обновления файла"""
        result = {
            'languages': [],
            'frameworks': [],
            'databases': [],
            'tools': [],
            'libraries': [],
            'package_managers': []
        }
        
        for item in tech_stack:
            tech_item = {
                'name': item['name'],
                'version': item['version'],
                'confidence': item['confidence'],
                'detected_by': item['detected_by']
            }
            
            # Простая категоризация (можно улучшить)
            name_lower = item['name'].lower()
            if any(lang in name_lower for lang in ['python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust']):
                result['languages'].append(tech_item)
            elif any(fw in name_lower for fw in ['react', 'vue', 'angular', 'django', 'flask', 'express', 'fastapi']):
                result['frameworks'].append(tech_item)
            elif any(db in name_lower for db in ['mysql', 'postgresql', 'sqlite', 'mongodb', 'redis']):
                result['databases'].append(tech_item)
            elif any(tool in name_lower for tool in ['docker', 'kubernetes', 'terraform', 'jenkins']):
                result['tools'].append(tech_item)
            elif any(pm in name_lower for pm in ['npm', 'pip', 'cargo', 'maven']):
                result['package_managers'].append(tech_item)
            else:
                result['libraries'].append(tech_item)
        
        return result
    
    def get_tech_stack_summary(self, project_id: int) -> str:
        """Получение краткой сводки технологического стека"""
        try:
            tech_stack = self.get_tech_stack_from_db(project_id)
            
            if not tech_stack:
                return "Технологический стек не определен"
            
            # Группируем по категориям
            categories = self._convert_db_to_dict(tech_stack)
            
            summary_parts = []
            
            # Основные технологии (топ-5 с наивысшей уверенностью)
            all_tech = []
            for category, items in categories.items():
                all_tech.extend([(item['name'], item['confidence']) for item in items])
            
            all_tech.sort(key=lambda x: x[1], reverse=True)
            top_tech = [name for name, _ in all_tech[:5]]
            
            if top_tech:
                summary_parts.append(f"Основные: {', '.join(top_tech)}")
            
            # Фреймворки
            if categories['frameworks']:
                frameworks = [fw['name'] for fw in categories['frameworks'][:3]]
                summary_parts.append(f"Фреймворки: {', '.join(frameworks)}")
            
            # Базы данных
            if categories['databases']:
                databases = [db['name'] for db in categories['databases']]
                summary_parts.append(f"БД: {', '.join(databases)}")
            
            return ' | '.join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения сводки технологического стека: {e}")
            return "Ошибка получения данных"
