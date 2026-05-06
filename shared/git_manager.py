import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

class GitManager:
    def __init__(self, project_path: str, db_manager):
        self.project_path = Path(project_path)
        self.db_manager = db_manager
        self.is_git_repo = False
        self.logger = logging.getLogger(__name__)
        
        # Проверяем наличие Git репозитория при инициализации
        self.check_git_repository()
    
    def check_git_repository(self) -> bool:
        """Проверка наличия Git репозитория"""
        try:
            git_dir = self.project_path / '.git'
            if git_dir.exists():
                self.is_git_repo = True
                self.logger.info(f"Git репозиторий найден в {self.project_path}")
                return True
            else:
                self.is_git_repo = False
                self.logger.info(f"Git репозиторий не найден в {self.project_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки Git репозитория: {e}")
            self.is_git_repo = False
            return False
    
    def _run_git_command(self, command: List[str]) -> Tuple[bool, str]:
        """Выполнение Git команды"""
        try:
            if not self.is_git_repo:
                return False, "Git репозиторий не найден"
            
            result = subprocess.run(
                ['git'] + command,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
                
        except subprocess.TimeoutExpired:
            return False, "Команда выполнена слишком долго"
        except Exception as e:
            return False, f"Ошибка выполнения команды: {e}"
    
    def get_commits(self, limit: int = 10) -> List[Dict]:
        """Получение последних коммитов"""
        try:
            if not self.is_git_repo:
                return []
            
            success, output = self._run_git_command([
                'log', 
                f'-{limit}',
                '--pretty=format:%H|%an|%s|%ci',
                '--name-only'
            ])
            
            if not success:
                self.logger.error(f"Ошибка получения коммитов: {output}")
                return []
            
            commits = []
            lines = output.split('\n')
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                if line and '|' in line:
                    # Парсим информацию о коммите
                    parts = line.split('|')
                    if len(parts) >= 4:
                        commit_hash = parts[0]
                        author = parts[1]
                        message = parts[2]
                        date_str = parts[3]
                        
                        # Собираем измененные файлы
                        files_changed = []
                        i += 1
                        while i < len(lines) and lines[i].strip():
                            file_path = lines[i].strip()
                            if file_path:
                                files_changed.append(file_path)
                            i += 1
                        
                        # Конвертируем дату
                        try:
                            commit_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z')
                            commit_date = commit_date.replace(tzinfo=None)  # Убираем timezone для sqlite
                        except:
                            commit_date = datetime.now()
                        
                        commits.append({
                            'commit_hash': commit_hash,
                            'author': author,
                            'message': message,
                            'date': commit_date,
                            'files_changed': files_changed,
                            'tags': []
                        })
                    else:
                        i += 1
                else:
                    i += 1
            
            # Получаем теги для коммитов
            commits = self._add_tags_to_commits(commits)
            
            self.logger.info(f"Получено {len(commits)} коммитов")
            return commits
            
        except Exception as e:
            self.logger.error(f"Ошибка получения коммитов: {e}")
            return []
    
    def _add_tags_to_commits(self, commits: List[Dict]) -> List[Dict]:
        """Добавление тегов к коммитам"""
        try:
            success, output = self._run_git_command(['tag', '--list'])
            if not success:
                return commits
            
            tags = output.split('\n')
            tag_map = {}
            
            # Для каждого тега получаем соответствующий коммит
            for tag in tags:
                tag = tag.strip()
                if tag:
                    success, commit_hash = self._run_git_command(['rev-list', '-n', '1', tag])
                    if success and commit_hash:
                        if commit_hash not in tag_map:
                            tag_map[commit_hash] = []
                        tag_map[commit_hash].append(tag)
            
            # Добавляем теги к коммитам
            for commit in commits:
                if commit['commit_hash'] in tag_map:
                    commit['tags'] = tag_map[commit['commit_hash']]
            
            return commits
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления тегов: {e}")
            return commits
    
    def get_tags(self) -> List[str]:
        """Получение тегов версий"""
        try:
            if not self.is_git_repo:
                return []
            
            success, output = self._run_git_command(['tag', '--list', '--sort=-version:refname'])
            if not success:
                return []
            
            tags = [tag.strip() for tag in output.split('\n') if tag.strip()]
            
            # Фильтруем только version-like теги
            version_pattern = re.compile(r'^v?\d+\.\d+\.\d+')
            version_tags = [tag for tag in tags if version_pattern.match(tag)]
            
            self.logger.info(f"Найдено {len(version_tags)} тегов версий")
            return version_tags
            
        except Exception as e:
            self.logger.error(f"Ошибка получения тегов: {e}")
            return []
    
    def get_current_branch(self) -> str:
        """Получение текущей ветки"""
        try:
            if not self.is_git_repo:
                return "main"
            
            success, output = self._run_git_command(['branch', '--show-current'])
            if success:
                branch = output.strip()
                return branch if branch else "main"
            else:
                return "main"
                
        except Exception as e:
            self.logger.error(f"Ошибка получения текущей ветки: {e}")
            return "main"
    
    def get_remote_url(self) -> str:
        """Получение URL удаленного репозитория"""
        try:
            if not self.is_git_repo:
                return ""
            
            success, output = self._run_git_command(['config', '--get', 'remote.origin.url'])
            if success:
                return output.strip()
            else:
                return ""
                
        except Exception as e:
            self.logger.error(f"Ошибка получения remote URL: {e}")
            return ""
    
    def get_git_status(self) -> Dict:
        """Получение статуса Git репозитория"""
        try:
            if not self.is_git_repo:
                return {
                    'is_clean': True,
                    'modified_files': [],
                    'untracked_files': [],
                    'staged_files': []
                }
            
            status = {
                'is_clean': True,
                'modified_files': [],
                'untracked_files': [],
                'staged_files': []
            }
            
            # Получаем статус
            success, output = self._run_git_command(['status', '--porcelain'])
            if not success:
                return status
            
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) >= 3:
                    status_code = line[:2]
                    file_path = line[3:]
                    
                    if status_code == '??':
                        status['untracked_files'].append(file_path)
                    elif status_code[0] in ['M', 'A', 'D', 'R', 'C']:
                        status['staged_files'].append(file_path)
                    elif status_code[1] in ['M', 'D']:
                        status['modified_files'].append(file_path)
            
            status['is_clean'] = not any([
                status['modified_files'],
                status['untracked_files'],
                status['staged_files']
            ])
            
            return status
            
        except Exception as e:
            self.logger.error(f"Ошибка получения статуса: {e}")
            return {
                'is_clean': True,
                'modified_files': [],
                'untracked_files': [],
                'staged_files': []
            }
    
    def update_git_context(self, project_id: int):
        """Обновление git_context.txt и сохранение в БД"""
        try:
            if not self.is_git_repo:
                self.logger.info("Git репозиторий не найден, контекст не обновлен")
                return
            
            # Получаем информацию о Git
            current_branch = self.get_current_branch()
            remote_url = self.get_remote_url()
            commits = self.get_commits(20)
            tags = self.get_tags()
            status = self.get_git_status()
            
            # Сохраняем коммиты в базу данных
            self._save_commits_to_db(project_id, commits)
            
            # Обновляем git_context.txt файл
            project_folder = self.db_manager.projects_dir / f"project_{project_id}"
            self._update_git_context_file(project_folder, current_branch, commits, tags, remote_url, status)
            
            # Обновляем технологический стек на основе Git
            self._update_tech_stack_from_git(project_id, commits)
            
            # Обновляем статус Git в проекте
            self.db_manager.conn.execute(
                "UPDATE projects SET git_enabled = TRUE WHERE id = ?",
                (project_id,)
            )
            self.db_manager.conn.commit()
            
            self.logger.info(f"Git контекст обновлен для проекта {project_id}")
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления Git контекста: {e}")
    
    def _save_commits_to_db(self, project_id: int, commits: List[Dict]):
        """Сохранение коммитов в базу данных"""
        try:
            # Очищаем старые коммиты
            self.db_manager.conn.execute(
                "DELETE FROM git_commits WHERE project_id = ?",
                (project_id,)
            )
            
            # Сохраняем новые коммиты
            for commit in commits:
                self.db_manager.conn.execute(
                    """
                    INSERT INTO git_commits 
                    (project_id, commit_hash, author, message, date, tags, files_changed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        commit['commit_hash'],
                        commit['author'],
                        commit['message'],
                        commit['date'],
                        json.dumps(commit['tags']),
                        json.dumps(commit['files_changed'])
                    )
                )
            
            self.db_manager.conn.commit()
            self.logger.info(f"Сохранено {len(commits)} коммитов в БД")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения коммитов в БД: {e}")
    
    def _update_git_context_file(self, project_folder: Path, branch: str, commits: List[Dict], 
                                tags: List[str], remote_url: str, status: Dict):
        """Обновление git_context.txt файла"""
        try:
            content = []
            content.append(f"=== GIT КОНТЕКСТ ===")
            content.append(f"Проект: {project_folder.name}")
            content.append(f"Ветка: {branch}")
            content.append(f"Remote: {remote_url}")
            
            if commits:
                last_commit = commits[0]
                content.append(f"Последний коммит: {last_commit['commit_hash'][:8]} ({last_commit['date'].strftime('%Y-%m-%d %H:%M:%S')})")
            
            content.append("")
            
            # Статус репозитория
            content.append("=== СТАТУС РЕПОЗИТОРИЯ ===")
            if status['is_clean']:
                content.append("✅ Репозиторий чистый")
            else:
                content.append("⚠️ Есть изменения:")
                if status['modified_files']:
                    content.append(f"  Измененные: {', '.join(status['modified_files'])}")
                if status['untracked_files']:
                    content.append(f"  Новые: {', '.join(status['untracked_files'])}")
                if status['staged_files']:
                    content.append(f"  В индексе: {', '.join(status['staged_files'])}")
            content.append("")
            
            # Последние коммиты
            if commits:
                content.append("=== ПОСЛЕДНИЕ КОММИТЫ ===")
                for commit in commits[:10]:  # Показываем последние 10
                    commit_hash = commit['commit_hash'][:8]
                    author = commit['author']
                    message = commit['message']
                    date_str = commit['date'].strftime('%Y-%m-%d %H:%M:%S')
                    tags_str = f" ({', '.join(commit['tags'])})" if commit['tags'] else ""
                    
                    content.append(f"{commit_hash} - {date_str} - {message} (Автор: {author}){tags_str}")
                content.append("")
            
            # Теги версий
            if tags:
                content.append("=== ТЕГИ ВЕРСИЙ ===")
                for tag in tags[:10]:  # Показываем последние 10
                    # Получаем коммит для тега
                    success, commit_hash = self._run_git_command(['rev-list', '-n', '1', tag])
                    if success:
                        content.append(f"{tag} -> {commit_hash[:8]}")
                content.append("")
            
            # Измененные файлы в последнем коммите
            if commits and commits[0]['files_changed']:
                content.append("=== ИЗМЕНЕННЫЕ ФАЙЛЫ ===")
                files = commits[0]['files_changed']
                if len(files) <= 10:
                    content.append(', '.join(files))
                else:
                    content.append(', '.join(files[:10]) + f" и еще {len(files) - 10} файлов")
                content.append("")
            
            with open(project_folder / "git_context.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления git_context.txt: {e}")
    
    def _update_tech_stack_from_git(self, project_id: int, commits: List[Dict]):
        """Обновление технологического стека на основе Git"""
        try:
            # Анализируем файлы в коммитах для определения технологий
            tech_files = set()
            
            for commit in commits:
                for file_path in commit['files_changed']:
                    file_ext = Path(file_path).suffix.lower()
                    
                    # Определяем технологии по расширениям файлов
                    if file_ext == '.py':
                        tech_files.add('Python')
                    elif file_ext in ['.js', '.jsx', '.ts', '.tsx']:
                        tech_files.add('JavaScript/TypeScript')
                    elif file_ext in ['.html', '.htm']:
                        tech_files.add('HTML')
                    elif file_ext == '.css':
                        tech_files.add('CSS')
                    elif file_ext in ['.java', '.jar']:
                        tech_files.add('Java')
                    elif file_ext in ['.cpp', '.c', '.h', '.hpp']:
                        tech_files.add('C/C++')
                    elif file_ext == '.go':
                        tech_files.add('Go')
                    elif file_ext == '.rs':
                        tech_files.add('Rust')
                    elif file_ext in ['.php']:
                        tech_files.add('PHP')
                    elif file_ext in ['.rb']:
                        tech_files.add('Ruby')
                    elif file_ext in ['.swift']:
                        tech_files.add('Swift')
                    elif file_ext in ['.kt']:
                        tech_files.add('Kotlin')
                    
                    # Файлы конфигурации
                    if file_path in ['package.json', 'yarn.lock', 'npm-shrinkwrap.json']:
                        tech_files.add('Node.js')
                    elif file_path in ['requirements.txt', 'Pipfile', 'poetry.lock', 'setup.py']:
                        tech_files.add('Python')
                    elif file_path in ['Cargo.toml', 'Cargo.lock']:
                        tech_files.add('Rust')
                    elif file_path in ['go.mod', 'go.sum']:
                        tech_files.add('Go')
                    elif file_path in ['pom.xml', 'build.gradle']:
                        tech_files.add('Java')
                    elif file_path in ['composer.json', 'composer.lock']:
                        tech_files.add('PHP')
            
            # Сохраняем технологии в базу данных
            for tech in tech_files:
                # Проверяем, существует ли уже технология
                cursor = self.db_manager.conn.execute(
                    "SELECT id FROM tech_stack WHERE project_id = ? AND technology = ?",
                    (project_id, tech)
                )
                existing = cursor.fetchone()
                
                if not existing:
                    self.db_manager.conn.execute(
                        """
                        INSERT INTO tech_stack (project_id, technology, detected_by, confidence)
                        VALUES (?, ?, 'git', 0.8)
                        """,
                        (project_id, tech)
                    )
            
            self.db_manager.conn.commit()
            self.logger.info(f"Обновлен технологический стек из Git: {list(tech_files)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления технологического стека из Git: {e}")
    
    def get_file_history(self, file_path: str, limit: int = 10) -> List[Dict]:
        """Получение истории изменений файла"""
        try:
            if not self.is_git_repo:
                return []
            
            success, output = self._run_git_command([
                'log',
                f'-{limit}',
                '--pretty=format:%H|%an|%s|%ci',
                '--',
                file_path
            ])
            
            if not success:
                return []
            
            history = []
            for line in output.split('\n'):
                if line and '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        history.append({
                            'commit_hash': parts[0],
                            'author': parts[1],
                            'message': parts[2],
                            'date': parts[3]
                        })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Ошибка получения истории файла: {e}")
            return []
    
    def analyze_dependencies_from_git(self, project_id: int) -> Dict:
        """Анализ зависимостей на основе Git истории"""
        try:
            if not self.is_git_repo:
                return {}
            
            dependencies = {
                'package_managers': set(),
                'libraries': set(),
                'frameworks': set(),
                'dev_tools': set()
            }
            
            # Получаем все файлы из истории коммитов
            success, output = self._run_git_command(['ls-tree', '-r', 'HEAD', '--name-only'])
            if not success:
                return {}
            
            files = output.split('\n')
            
            # Анализируем файлы для определения зависимостей
            for file_path in files:
                file_path = file_path.strip()
                if not file_path:
                    continue
                
                # Менеджеры пакетов
                if file_path in ['package.json', 'yarn.lock', 'npm-shrinkwrap.json', 'pnpm-lock.yaml']:
                    dependencies['package_managers'].add('npm/yarn/pnpm')
                    # Анализируем package.json
                    if file_path == 'package.json':
                        deps = self._analyze_package_json(project_id)
                        dependencies['libraries'].update(deps['libraries'])
                        dependencies['frameworks'].update(deps['frameworks'])
                
                elif file_path in ['requirements.txt', 'Pipfile', 'poetry.lock', 'setup.py', 'pyproject.toml']:
                    dependencies['package_managers'].add('pip/poetry')
                    # Анализируем requirements.txt
                    if file_path == 'requirements.txt':
                        deps = self._analyze_requirements_txt(project_id)
                        dependencies['libraries'].update(deps['libraries'])
                        dependencies['frameworks'].update(deps['frameworks'])
                
                elif file_path in ['Cargo.toml', 'Cargo.lock']:
                    dependencies['package_managers'].add('cargo')
                
                elif file_path in ['go.mod', 'go.sum']:
                    dependencies['package_managers'].add('go modules')
                
                elif file_path in ['pom.xml', 'build.gradle', 'build.gradle.kts']:
                    dependencies['package_managers'].add('maven/gradle')
                
                elif file_path in ['composer.json', 'composer.lock']:
                    dependencies['package_managers'].add('composer')
                
                # DevOps инструменты
                elif file_path in ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']:
                    dependencies['dev_tools'].add('Docker')
                elif file_path in ['.github/workflows', '.gitlab-ci.yml', 'Jenkinsfile']:
                    dependencies['dev_tools'].add('CI/CD')
                elif file_path.endswith(('.tf', '.tfvars')):
                    dependencies['dev_tools'].add('Terraform')
                elif file_path in ['k8s/', 'kubernetes/', 'deployment.yaml', 'service.yaml']:
                    dependencies['dev_tools'].add('Kubernetes')
            
            # Сохраняем результаты в базу данных
            self._save_dependencies_to_db(project_id, dependencies)
            
            return {k: list(v) for k, v in dependencies.items()}
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа зависимостей из Git: {e}")
            return {}
    
    def _analyze_package_json(self, project_id: int) -> Dict:
        """Анализ package.json файла"""
        try:
            success, output = self._run_git_command(['show', 'HEAD:package.json'])
            if not success:
                return {'libraries': set(), 'frameworks': set()}
            
            import json
            package_data = json.loads(output)
            
            libraries = set()
            frameworks = set()
            
            # Анализируем зависимости
            all_deps = {}
            all_deps.update(package_data.get('dependencies', {}))
            all_deps.update(package_data.get('devDependencies', {}))
            
            for dep_name in all_deps.keys():
                # Определяем тип зависимости
                if dep_name in ['react', 'react-dom']:
                    frameworks.add('React')
                elif dep_name in ['vue']:
                    frameworks.add('Vue.js')
                elif dep_name in ['angular', '@angular/core']:
                    frameworks.add('Angular')
                elif dep_name in ['express']:
                    frameworks.add('Express.js')
                elif dep_name in ['next']:
                    frameworks.add('Next.js')
                elif dep_name in ['nuxt']:
                    frameworks.add('Nuxt.js')
                elif dep_name in ['django', 'flask', 'fastapi']:
                    frameworks.add(dep_name.title())
                else:
                    libraries.add(dep_name)
            
            return {'libraries': libraries, 'frameworks': frameworks}
            
        except Exception as e:
            self.logger.warning(f"Ошибка анализа package.json: {e}")
            return {'libraries': set(), 'frameworks': set()}
    
    def _analyze_requirements_txt(self, project_id: int) -> Dict:
        """Анализ requirements.txt файла"""
        try:
            success, output = self._run_git_command(['show', 'HEAD:requirements.txt'])
            if not success:
                return {'libraries': set(), 'frameworks': set()}
            
            libraries = set()
            frameworks = set()
            
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Извлекаем имя библиотеки
                    lib_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
                    lib_name = lib_name.strip()
                    
                    if lib_name:
                        # Определяем тип зависимости
                        if lib_name in ['django', 'flask', 'fastapi']:
                            frameworks.add(lib_name.title())
                        elif lib_name in ['tensorflow', 'torch', 'keras']:
                            frameworks.add('ML/AI')
                        elif lib_name in ['numpy', 'pandas', 'matplotlib', 'scipy']:
                            libraries.add(lib_name)
                        else:
                            libraries.add(lib_name)
            
            return {'libraries': libraries, 'frameworks': frameworks}
            
        except Exception as e:
            self.logger.warning(f"Ошибка анализа requirements.txt: {e}")
            return {'libraries': set(), 'frameworks': set()}
    
    def _save_dependencies_to_db(self, project_id: int, dependencies: Dict):
        """Сохранение зависимостей в базу данных"""
        try:
            # Сохраняем библиотеки
            for lib in dependencies['libraries']:
                cursor = self.db_manager.conn.execute(
                    "SELECT id FROM tech_stack WHERE project_id = ? AND technology = ?",
                    (project_id, lib)
                )
                if not cursor.fetchone():
                    self.db_manager.conn.execute(
                        """
                        INSERT INTO tech_stack (project_id, technology, detected_by, confidence)
                        VALUES (?, ?, 'git_analysis', 0.9)
                        """,
                        (project_id, lib)
                    )
            
            # Сохраняем фреймворки
            for framework in dependencies['frameworks']:
                cursor = self.db_manager.conn.execute(
                    "SELECT id FROM tech_stack WHERE project_id = ? AND technology = ?",
                    (project_id, framework)
                )
                if not cursor.fetchone():
                    self.db_manager.conn.execute(
                        """
                        INSERT INTO tech_stack (project_id, technology, detected_by, confidence)
                        VALUES (?, ?, 'git_analysis', 0.9)
                        """,
                        (project_id, framework)
                    )
            
            # Сохраняем инструменты
            for tool in dependencies['dev_tools']:
                cursor = self.db_manager.conn.execute(
                    "SELECT id FROM tech_stack WHERE project_id = ? AND technology = ?",
                    (project_id, tool)
                )
                if not cursor.fetchone():
                    self.db_manager.conn.execute(
                        """
                        INSERT INTO tech_stack (project_id, technology, detected_by, confidence)
                        VALUES (?, ?, 'git_analysis', 0.9)
                        """,
                        (project_id, tool)
                    )
            
            self.db_manager.conn.commit()
            self.logger.info(f"Сохранены зависимости для проекта {project_id}")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения зависимостей: {e}")
