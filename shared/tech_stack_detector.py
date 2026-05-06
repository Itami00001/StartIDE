import re
import json
from pathlib import Path
from typing import Dict, List, Set, Optional
import logging
from datetime import datetime

class TechStackDetector:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.logger = logging.getLogger(__name__)
        
        # Словари для определения технологий
        self.python_patterns = {
            'import_patterns': [
                r'import\s+(tkinter|pygame|flask|django|fastapi|numpy|pandas|matplotlib|scipy|sklearn|tensorflow|pytorch|keras|opencv|pillow|requests|beautifulsoup|selenium|sqlalchemy|pymongo|psycopg2)',
                r'from\s+(tkinter|pygame|flask|django|fastapi|numpy|pandas|matplotlib|scipy|sklearn|tensorflow|pytorch|keras|opencv|pillow|requests|beautifulsoup|selenium|sqlalchemy|pymongo|psycopg2)\s+import'
            ],
            'requirements_files': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
            'config_files': ['django.conf', 'flask_config.py']
        }
        
        self.javascript_patterns = {
            'import_patterns': [
                r'import\s+(react|vue|angular|express|lodash|moment|axios|jquery|bootstrap|tailwind)',
                r'require\s*\([\'"]((react|vue|angular|express|lodash|moment|axios|jquery|bootstrap|tailwind)[^\'\"]*)[\'"]',
                r'from\s+[\'"]((react|vue|angular|express|lodash|moment|axios|jquery|bootstrap|tailwind)[^\'\"]*)[\'"]'
            ],
            'package_files': ['package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'],
            'config_files': ['webpack.config.js', 'vite.config.js', 'rollup.config.js']
        }
        
        self.web_patterns = {
            'html_files': ['*.html', '*.htm'],
            'css_files': ['*.css', '*.scss', '*.sass', '*.less'],
            'framework_indicators': [
                r'<(html|head|body|div|span|script|style|link)>',
                r'(class|id)\s*=\s*["\'][^"\']*["\']',
                r'@[keyframes|media|font-face]'
            ]
        }
        
        self.database_patterns = {
            'sql_files': ['*.sql', '*.db', '*.sqlite', '*.sqlite3'],
            'orm_patterns': [
                r'(SQLAlchemy|Django ORM|Peewee|SQLObject|Tortoise ORM)',
                r'(CREATE TABLE|INSERT INTO|SELECT|UPDATE|DELETE FROM)'
            ],
            'config_files': ['database.yml', 'db_config.py', 'models.py']
        }
        
        self.devops_patterns = {
            'docker_files': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
            'ci_files': ['.github/workflows/*.yml', '.gitlab-ci.yml', 'Jenkinsfile'],
            'k8s_files': ['*.yaml', '*.yml', 'k8s/', 'kubernetes/']
        }
    
    def detect_tech_stack(self) -> Dict[str, List[Dict]]:
        """Основной метод определения технологического стека"""
        tech_stack = {
            'languages': [],
            'frameworks': [],
            'databases': [],
            'tools': [],
            'libraries': []
        }
        
        try:
            # Анализ файлов проекта
            files = self._get_project_files()
            
            # Определение языков программирования
            detected_languages = self._detect_languages(files)
            tech_stack['languages'].extend(detected_languages)
            
            # Определение фреймворков
            detected_frameworks = self._detect_frameworks(files)
            tech_stack['frameworks'].extend(detected_frameworks)
            
            # Определение баз данных
            detected_databases = self._detect_databases(files)
            tech_stack['databases'].extend(detected_databases)
            
            # Определение инструментов разработки
            detected_tools = self._detect_devops_tools(files)
            tech_stack['tools'].extend(detected_tools)
            
            # Определение библиотек
            detected_libraries = self._detect_libraries(files)
            tech_stack['libraries'].extend(detected_libraries)
            
            # Удаление дубликатов и сортировка
            for category in tech_stack:
                tech_stack[category] = self._deduplicate_and_sort(tech_stack[category])
            
            self.logger.info(f"Обнаружен технологический стек: {tech_stack}")
            
        except Exception as e:
            self.logger.error(f"Ошибка определения технологического стека: {e}")
        
        return tech_stack
    
    def _get_project_files(self) -> List[Path]:
        """Получает список файлов проекта"""
        files = []
        try:
            for file_path in self.project_path.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    files.append(file_path)
        except Exception as e:
            self.logger.error(f"Ошибка получения файлов проекта: {e}")
        return files
    
    def _detect_languages(self, files: List[Path]) -> List[Dict]:
        """Определяет языки программирования"""
        languages = []
        language_extensions = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.html': 'HTML',
            '.css': 'CSS',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.ps1': 'PowerShell'
        }
        
        extension_counts = {}
        for file_path in files:
            ext = file_path.suffix.lower()
            if ext in language_extensions:
                extension_counts[ext] = extension_counts.get(ext, 0) + 1
        
        for ext, count in extension_counts.items():
            if ext in language_extensions:
                language = language_extensions[ext]
                confidence = min(count / 10, 1.0)  # Чем больше файлов, тем выше уверенность
                languages.append({
                    'name': language,
                    'version': self._detect_language_version(language),
                    'confidence': confidence,
                    'detected_by': 'file_analysis'
                })
        
        return languages
    
    def _detect_language_version(self, language: str) -> Optional[str]:
        """Пытается определить версию языка"""
        version_patterns = {
            'Python': [r'python\s*([3-9]\.[0-9]+)', r'#!/usr/bin/python([3-9]\.[0-9]+)'],
            'JavaScript': [r'"engines":\s*{[^}]*"node":\s*"([^"]+)"'],
            'Java': [r'version\s*["\']?([1-9][0-9]*\.[0-9]+)'],
            'Ruby': [r'ruby\s*"([0-9]+\.[0-9]+)"']
        }
        
        if language not in version_patterns:
            return None
        
        try:
            for file_path in self._get_project_files():
                if file_path.suffix in ['.py', '.js', '.java', '.rb', '.json', '.gemfile']:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        for pattern in version_patterns[language]:
                            match = re.search(pattern, content, re.IGNORECASE)
                            if match:
                                return match.group(1)
        except Exception as e:
            self.logger.warning(f"Ошибка определения версии {language}: {e}")
        
        return None
    
    def _detect_frameworks(self, files: List[Path]) -> List[Dict]:
        """Определяет фреймворки"""
        frameworks = []
        
        # Python фреймворки
        python_frameworks = {
            'Django': ['django.conf', 'settings.py', 'wsgi.py', 'asgi.py'],
            'Flask': ['app.py', 'flask', 'Flask'],
            'FastAPI': ['fastapi', 'FastAPI', 'main.py'],
            'Tkinter': ['tkinter', 'Tkinter'],
            'Pygame': ['pygame', 'Pygame'],
            'TensorFlow': ['tensorflow', 'TensorFlow'],
            'PyTorch': ['torch', 'PyTorch']
        }
        
        # JavaScript фреймворки
        js_frameworks = {
            'React': ['react', 'React', 'jsx', 'tsx'],
            'Vue': ['vue', 'Vue', '.vue'],
            'Angular': ['angular', 'Angular'],
            'Express': ['express', 'Express'],
            'Next.js': ['next', 'Next.js']
        }
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Проверка Python фреймворков
                    for framework, indicators in python_frameworks.items():
                        if any(indicator in content for indicator in indicators):
                            frameworks.append({
                                'name': framework,
                                'version': self._detect_framework_version(framework, content),
                                'confidence': 0.8,
                                'detected_by': 'code_analysis'
                            })
                    
                    # Проверка JavaScript фреймворков
                    for framework, indicators in js_frameworks.items():
                        if any(indicator in content for indicator in indicators):
                            frameworks.append({
                                'name': framework,
                                'version': self._detect_framework_version(framework, content),
                                'confidence': 0.8,
                                'detected_by': 'code_analysis'
                            })
                            
            except Exception as e:
                self.logger.warning(f"Ошибка анализа файла {file_path}: {e}")
        
        return frameworks
    
    def _detect_framework_version(self, framework: str, content: str) -> Optional[str]:
        """Определяет версию фреймворка"""
        version_patterns = {
            'Django': [r'Django\s*([0-9]+\.[0-9]+)', r'VERSION\s*=\s*["\']([0-9]+\.[0-9]+)'],
            'Flask': [r'Flask\s*([0-9]+\.[0-9]+)', r'__version__\s*=\s*["\']([0-9]+\.[0-9]+)'],
            'React': [r'"react":\s*"([^"]+)"', r'react@([0-9]+\.[0-9]+)'],
            'Vue': [r'"vue":\s*"([^"]+)"', r'vue@([0-9]+\.[0-9]+)'],
            'Angular': [r'"@angular/core":\s*"([^"]+)"']
        }
        
        if framework not in version_patterns:
            return None
        
        for pattern in version_patterns[framework]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _detect_databases(self, files: List[Path]) -> List[Dict]:
        """Определяет базы данных"""
        databases = []
        
        database_indicators = {
            'SQLite': ['sqlite3', 'SQLite', '.db', '.sqlite'],
            'PostgreSQL': ['postgresql', 'psycopg2', 'postgres'],
            'MySQL': ['mysql', 'pymysql', 'mysql-connector'],
            'MongoDB': ['mongodb', 'pymongo', 'MongoClient'],
            'Redis': ['redis', 'redis-py'],
            'Elasticsearch': ['elasticsearch', 'Elasticsearch']
        }
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    for db_name, indicators in database_indicators.items():
                        if any(indicator in content for indicator in indicators):
                            databases.append({
                                'name': db_name,
                                'version': None,
                                'confidence': 0.7,
                                'detected_by': 'code_analysis'
                            })
                            break
                            
            except Exception as e:
                self.logger.warning(f"Ошибка анализа файла {file_path}: {e}")
        
        return databases
    
    def _detect_devops_tools(self, files: List[Path]) -> List[Dict]:
        """Определяет DevOps инструменты"""
        tools = []
        
        tool_files = {
            'Docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
            'Git': ['.git', '.gitignore', '.gitattributes'],
            'GitHub Actions': ['.github/workflows'],
            'GitLab CI': ['.gitlab-ci.yml'],
            'Jenkins': ['Jenkinsfile'],
            'Kubernetes': ['k8s', 'kubernetes', 'deployment.yaml'],
            'Terraform': ['*.tf', 'terraform.tfstate'],
            'Ansible': ['*.yml', 'playbook']
        }
        
        for tool_name, file_patterns in tool_files.items():
            for file_path in files:
                for pattern in file_patterns:
                    if pattern.startswith('*.'):
                        if file_path.suffix == pattern[1:]:
                            tools.append({
                                'name': tool_name,
                                'version': None,
                                'confidence': 0.9,
                                'detected_by': 'file_analysis'
                            })
                            break
                    else:
                        if pattern in str(file_path):
                            tools.append({
                                'name': tool_name,
                                'version': None,
                                'confidence': 0.9,
                                'detected_by': 'file_analysis'
                            })
                            break
        
        return tools
    
    def _detect_libraries(self, files: List[Path]) -> List[Dict]:
        """Определяет библиотеки"""
        libraries = []
        
        # Анализ requirements.txt
        req_file = self.project_path / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            lib_name = line.split('==')[0].split('>=')[0].split('<=')[0]
                            libraries.append({
                                'name': lib_name,
                                'version': self._extract_version_from_requirement(line),
                                'confidence': 0.9,
                                'detected_by': 'requirements_file'
                            })
            except Exception as e:
                self.logger.warning(f"Ошибка чтения requirements.txt: {e}")
        
        # Анализ package.json
        package_file = self.project_path / 'package.json'
        if package_file.exists():
            try:
                with open(package_file, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    dependencies = package_data.get('dependencies', {})
                    for lib_name, version in dependencies.items():
                        libraries.append({
                            'name': lib_name,
                            'version': version,
                            'confidence': 0.9,
                            'detected_by': 'package_file'
                        })
            except Exception as e:
                self.logger.warning(f"Ошибка чтения package.json: {e}")
        
        return libraries
    
    def _extract_version_from_requirement(self, requirement: str) -> Optional[str]:
        """Извлекает версию из строки требования"""
        version_patterns = [
            r'==\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
            r'>=\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
            r'<=\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
            r'~=\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)'
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, requirement)
            if match:
                return match.group(1)
        
        return None
    
    def _deduplicate_and_sort(self, items: List[Dict]) -> List[Dict]:
        """Удаляет дубликаты и сортирует по уверенности"""
        seen = set()
        unique_items = []
        
        for item in items:
            key = (item['name'], item.get('detected_by', ''))
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        
        return sorted(unique_items, key=lambda x: x['confidence'], reverse=True)
    
    def generate_tech_stack_report(self) -> str:
        """Генерирует текстовый отчет о технологическом стеке"""
        tech_stack = self.detect_tech_stack()
        
        report = []
        report.append("=== ТЕХНОЛОГИЧЕСКИЙ СТЕК ===")
        report.append(f"Проект: {self.project_path.name}")
        report.append(f"Обновлено: {datetime.now().isoformat()}")
        report.append("")
        
        for category, items in tech_stack.items():
            if items:
                category_names = {
                    'languages': 'ОСНОВНЫЕ ЯЗЫКИ',
                    'frameworks': 'ФРЕЙМВОРКИ',
                    'databases': 'БАЗЫ ДАННЫХ',
                    'tools': 'ИНСТРУМЕНТЫ РАЗРАБОТКИ',
                    'libraries': 'БИБЛИОТЕКИ'
                }
                
                report.append(f"=== {category_names.get(category, category.upper())} ===")
                for item in items:
                    version = f" {item['version']}" if item['version'] else ""
                    confidence = f" (уверенность: {item['confidence']:.1f})"
                    detected_by = f" - {item['detected_by']}"
                    report.append(f"{item['name']}{version}{confidence}{detected_by}")
                report.append("")
        
        return "\n".join(report)
