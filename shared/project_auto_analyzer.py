import json
from pathlib import Path
from typing import Dict, Optional, List
import logging
from datetime import datetime
from .tech_stack_detector import TechStackDetector
from .git_manager import GitManager

class ProjectAutoAnalyzer:
    """Автоматический анализатор проектов для определения данных без ручного ввода"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def analyze_project(self, project_path: str) -> Dict:
        """Полный автоматический анализ проекта"""
        try:
            path = Path(project_path)
            if not path.exists():
                return {}
            
            # Базовая информация о проекте
            project_info = {
                'name': self._detect_project_name(path),
                'path': str(path),
                'description': self._generate_description(path),
                'type': self._detect_project_type(path),
                'created': datetime.now().isoformat(),
                'auto_detected': True
            }
            
            # Технологический стек
            tech_detector = TechStackDetector(str(path))
            tech_stack = tech_detector.detect_tech_stack()
            project_info['tech_stack'] = tech_stack
            
            # Git информация
            git_manager = GitManager(str(path), self.db_manager)
            if git_manager.is_git_repo:
                git_info = self._extract_git_info(git_manager)
                project_info['git_info'] = git_info
            
            # Структура проекта
            structure = self._analyze_project_structure(path)
            project_info['structure'] = structure
            
            # Ключевые файлы
            key_files = self._identify_key_files(path)
            project_info['key_files'] = key_files
            
            # Метаданные
            metadata = self._extract_metadata(path)
            project_info['metadata'] = metadata
            
            self.logger.info(f"Проанализирован проект: {project_info['name']}")
            return project_info
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа проекта {project_path}: {e}")
            return {}
    
    def _detect_project_name(self, path: Path) -> str:
        """Автоопределение имени проекта"""
        # 1. Имя папки проекта
        folder_name = path.name
        
        # 2. Проверяем package.json
        package_json = path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'name' in data:
                        return data['name']
            except:
                pass
        
        # 3. Проверяем setup.py или pyproject.toml
        setup_py = path / "setup.py"
        if setup_py.exists():
            try:
                with open(setup_py, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Ищем имя в setup()
                    import re
                    match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        return match.group(1)
            except:
                pass
        
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            try:
                with open(pyproject, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Ищем имя в [project]
                    import re
                    match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        return match.group(1)
            except:
                pass
        
        # 4. Проверяем pom.xml
        pom_xml = path / "pom.xml"
        if pom_xml.exists():
            try:
                with open(pom_xml, 'r', encoding='utf-8') as f:
                    content = f.read()
                    import re
                    match = re.search(r'<artifactId>([^<]+)</artifactId>', content)
                    if match:
                        return match.group(1)
            except:
                pass
        
        # 5. Возвращаем имя папки как запасной вариант
        return folder_name
    
    def _generate_description(self, path: Path) -> str:
        """Автоматическая генерация описания проекта"""
        description_parts = []
        
        # Тип проекта
        project_type = self._detect_project_type(path)
        if project_type:
            description_parts.append(f"Проект типа {project_type}")
        
        # Основные технологии
        tech_detector = TechStackDetector(str(path))
        tech_stack = tech_detector.detect_tech_stack()
        
        main_techs = []
        if tech_stack.get('languages'):
            main_techs.extend([lang['name'] for lang in tech_stack['languages'][:2]])
        if tech_stack.get('frameworks'):
            main_techs.extend([fw['name'] for fw in tech_stack['frameworks'][:1]])
        
        if main_techs:
            description_parts.append(f"на {', '.join(main_techs)}")
        
        # Git репозиторий
        git_manager = GitManager(str(path), self.db_manager)
        if git_manager.is_git_repo:
            description_parts.append("с Git контролем версий")
        
        # Ключевые файлы
        key_files = self._identify_key_files(path)
        if key_files:
            file_types = []
            for file_info in key_files[:3]:
                file_types.append(file_info['type'])
            description_parts.append(f"с файлами {', '.join(file_types)}")
        
        return " ".join(description_parts) if description_parts else "Программный проект"
    
    def _detect_project_type(self, path: Path) -> str:
        """Определение типа проекта"""
        indicators = {
            'Web-приложение': ['package.json', 'index.html', 'app.js', 'main.js', 'public/'],
            'Python-приложение': ['requirements.txt', 'setup.py', 'pyproject.toml', 'main.py', 'app.py'],
            'Java-приложение': ['pom.xml', 'build.gradle', 'src/main/java/'],
            'C++ приложение': ['CMakeLists.txt', 'Makefile', 'main.cpp', 'src/'],
            'Go приложение': ['go.mod', 'main.go', 'cmd/'],
            'Rust приложение': ['Cargo.toml', 'src/main.rs'],
            'PHP приложение': ['composer.json', 'index.php', 'public/'],
            'Ruby приложение': ['Gemfile', 'app/', 'config/'],
            'Мобильное приложение': ['android/', 'ios/', 'lib/', 'pubspec.yaml'],
            'Библиотека': ['lib/', 'src/', 'include/'],
            'Data Science проект': ['notebooks/', 'data/', 'jupyter/', 'requirements.txt']
        }
        
        for project_type, files in indicators.items():
            matches = 0
            for file_pattern in files:
                if file_pattern.endswith('/'):
                    # Проверка папки
                    if (path / file_pattern).exists():
                        matches += 1
                else:
                    # Проверка файла
                    if (path / file_pattern).exists():
                        matches += 1
            
            # Если найдено больше половины индикаторов
            if matches >= len(files) // 2 + 1:
                return project_type
        
        return "Неопределенный проект"
    
    def _analyze_project_structure(self, path: Path) -> Dict:
        """Анализ структуры проекта"""
        structure = {
            'folders': [],
            'files': [],
            'total_size': 0,
            'file_count': 0,
            'folder_count': 0
        }
        
        try:
            for item in path.iterdir():
                if item.name.startswith('.'):
                    continue
                
                if item.is_dir():
                    structure['folders'].append({
                        'name': item.name,
                        'path': str(item.relative_to(path))
                    })
                    structure['folder_count'] += 1
                elif item.is_file():
                    try:
                        size = item.stat().st_size
                        structure['files'].append({
                            'name': item.name,
                            'path': str(item.relative_to(path)),
                            'size': size,
                            'extension': item.suffix.lower()
                        })
                        structure['total_size'] += size
                        structure['file_count'] += 1
                    except:
                        continue
        except Exception as e:
            self.logger.warning(f"Ошибка анализа структуры: {e}")
        
        return structure
    
    def _identify_key_files(self, path: Path) -> List[Dict]:
        """Определение ключевых файлов проекта"""
        key_files = []
        
        # Конфигурационные файлы
        config_patterns = {
            'package.json': 'Node.js конфигурация',
            'requirements.txt': 'Python зависимости',
            'setup.py': 'Python setup',
            'pyproject.toml': 'Python конфигурация',
            'pom.xml': 'Maven конфигурация',
            'build.gradle': 'Gradle конфигурация',
            'Cargo.toml': 'Rust конфигурация',
            'go.mod': 'Go модули',
            'composer.json': 'PHP зависимости',
            'Gemfile': 'Ruby зависимости',
            'Dockerfile': 'Docker конфигурация',
            'docker-compose.yml': 'Docker Compose',
            'Makefile': 'Make конфигурация',
            'CMakeLists.txt': 'CMake конфигурация'
        }
        
        # Основные файлы
        main_patterns = {
            'main.py': 'Python основной файл',
            'app.py': 'Python основной файл',
            'index.js': 'JavaScript основной файл',
            'app.js': 'JavaScript основной файл',
            'main.js': 'JavaScript основной файл',
            'index.html': 'HTML основной файл',
            'index.php': 'PHP основной файл',
            'main.cpp': 'C++ основной файл',
            'main.go': 'Go основной файл',
            'main.rs': 'Rust основной файл',
            'Main.java': 'Java основной файл'
        }
        
        all_patterns = {**config_patterns, **main_patterns}
        
        for file_name, file_type in all_patterns.items():
            file_path = path / file_name
            if file_path.exists():
                try:
                    size = file_path.stat().st_size
                    key_files.append({
                        'name': file_name,
                        'path': str(file_path),
                        'type': file_type,
                        'size': size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
                except:
                    continue
        
        return key_files
    
    def _extract_git_info(self, git_manager: GitManager) -> Dict:
        """Извлечение Git информации"""
        if not git_manager.is_git_repo:
            return {}
        
        try:
            git_info = {
                'is_git_repo': True,
                'current_branch': git_manager.get_current_branch(),
                'remote_url': git_manager.get_remote_url(),
                'last_commit': None,
                'total_commits': 0,
                'tags': []
            }
            
            # Последний коммит
            commits = git_manager.get_commits(1)
            if commits:
                last_commit = commits[0]
                git_info['last_commit'] = {
                    'hash': last_commit['commit_hash'][:8],
                    'author': last_commit['author'],
                    'message': last_commit['message'],
                    'date': last_commit['date'].isoformat()
                }
            
            # Теги
            git_info['tags'] = git_manager.get_tags()
            
            # Статус
            status = git_manager.get_git_status()
            git_info['is_clean'] = status['is_clean']
            
            return git_info
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения Git информации: {e}")
            return {'is_git_repo': False}
    
    def _extract_metadata(self, path: Path) -> Dict:
        """Извлечение метаданных проекта"""
        metadata = {
            'created_date': None,
            'modified_date': None,
            'main_language': None,
            'frameworks': [],
            'has_tests': False,
            'has_docs': False,
            'has_ci_cd': False
        }
        
        try:
            # Даты создания и модификации
            stats = path.stat()
            metadata['created_date'] = datetime.fromtimestamp(stats.st_ctime).isoformat()
            metadata['modified_date'] = datetime.fromtimestamp(stats.st_mtime).isoformat()
            
            # Основной язык
            tech_detector = TechStackDetector(str(path))
            tech_stack = tech_detector.detect_tech_stack()
            
            if tech_stack.get('languages'):
                metadata['main_language'] = tech_stack['languages'][0]['name']
            
            if tech_stack.get('frameworks'):
                metadata['frameworks'] = [fw['name'] for fw in tech_stack['frameworks']]
            
            # Наличие тестов
            test_indicators = ['test/', 'tests/', '__tests__/', 'spec/', 'test_*.py', '*_test.py', '*.test.js']
            for indicator in test_indicators:
                if '*' in indicator:
                    # Проверка по маске
                    for item in path.glob(indicator):
                        if item.is_file():
                            metadata['has_tests'] = True
                            break
                else:
                    if (path / indicator).exists():
                        metadata['has_tests'] = True
                        break
            
            # Наличие документации
            doc_indicators = ['docs/', 'doc/', 'README.md', 'readme.md', 'CHANGELOG.md', 'API.md']
            for indicator in doc_indicators:
                if (path / indicator).exists():
                    metadata['has_docs'] = True
                    break
            
            # Наличие CI/CD
            ci_indicators = ['.github/', '.gitlab-ci.yml', 'Jenkinsfile', '.travis.yml', 'appveyor.yml']
            for indicator in ci_indicators:
                if (path / indicator).exists():
                    metadata['has_ci_cd'] = True
                    break
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения метаданных: {e}")
        
        return metadata
    
    def create_project_auto(self, project_path: str) -> Optional[int]:
        """Создание проекта в БД на основе автоанализа"""
        try:
            # Анализируем проект
            project_data = self.analyze_project(project_path)
            
            if not project_data:
                self.logger.error(f"Не удалось проанализировать проект: {project_path}")
                return None
            
            # Создаем проект в БД
            project_id = self.db_manager.create_project(
                name=project_data['name'],
                path=project_data['path'],
                description=project_data['description']
            )
            
            if project_id:
                # Сохраняем технологический стек
                self._save_tech_stack(project_id, project_data.get('tech_stack', {}))
                
                # Обновляем Git контекст
                git_manager = GitManager(project_path, self.db_manager)
                if git_manager.is_git_repo:
                    git_manager.update_git_context(project_id)
                
                # Сохраняем метаданные
                self._save_metadata(project_id, project_data.get('metadata', {}))
                
                self.logger.info(f"Проект автоматически создан: {project_data['name']} (ID: {project_id})")
                return project_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка авто-создания проекта: {e}")
            return None
    
    def _save_tech_stack(self, project_id: int, tech_stack: Dict):
        """Сохранение технологического стека"""
        try:
            for category, items in tech_stack.items():
                for item in items:
                    self.db_manager.conn.execute(
                        """
                        INSERT INTO tech_stack (project_id, technology, version, detected_by, confidence)
                        VALUES (?, ?, ?, 'auto', ?)
                        """,
                        (project_id, item['name'], item.get('version'), item.get('confidence', 0.7))
                    )
            self.db_manager.conn.commit()
        except Exception as e:
            self.logger.error(f"Ошибка сохранения технологического стека: {e}")
    
    def _save_metadata(self, project_id: int, metadata: Dict):
        """Сохранение метаданных"""
        try:
            # Можно сохранить в отдельную таблицу или в JSON поле
            metadata_json = json.dumps(metadata, ensure_ascii=False, default=str)
            
            # Временно сохраняем в таблицу проектов (можно добавить отдельное поле)
            self.db_manager.conn.execute(
                "UPDATE projects SET description = description || ? WHERE id = ?",
                (f"\n\nМетаданные: {metadata_json}", project_id)
            )
            self.db_manager.conn.commit()
        except Exception as e:
            self.logger.error(f"Ошибка сохранения метаданных: {e}")
