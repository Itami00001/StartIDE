import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import os
from pathlib import Path
import threading
import logging
from typing import Dict

# Добавляем путь к shared модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.ollama_manager import OllamaManager
from shared.project_context import ProjectContext
from shared.shared_chat_manager import SharedChatManager
from shared.database_manager import DatabaseManager
from shared.git_manager import GitManager
from shared.app_logger import AppLogger
from shared.project_manager import ProjectManager
from shared.file_tracker import FileTracker

# Опциональный импорт голосового менеджера
try:
    from StartIDE.voice_manager import VoiceManager
    from StartIDE.advanced_voice_manager import AdvancedVoiceManager
    from StartIDE.project_manager_window import ProjectManagerWindow
    VOICE_AVAILABLE = True
    ADVANCED_VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    ADVANCED_VOICE_AVAILABLE = False
    VoiceManager = None
    AdvancedVoiceManager = None

class StartIDE:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("StartIDE")
        self.root.geometry("1200x800")
        
        # Переменные проекта
        self.project_path = None
        self.ollama_manager = None
        self.project_context = None
        self.shared_chat_manager = None
        self.last_chat_timestamp = None
        
        # Новая система баз данных
        self.db_manager = None
        self.git_manager = None
        self.current_project_id = None
        
        # Голосовой менеджер для AI чата
        self.voice_manager = None
        self.advanced_voice_manager = None
        
        # Управление проектами и файлами
        self.project_manager = None
        self.file_tracker = None
        
        # Разделенное логирование
        self.app_logger = None
        
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Привязка горячих клавиш
        self.root.bind('<Control-s>', lambda e: self.save_current_file())
        self.root.bind('<Control-S>', lambda e: self.save_current_file())
        self.root.bind('<Control-q>', lambda e: self.quit_app())
        
        # Инициализация новой системы баз данных
        self.init_database()
        
        # Создание интерфейса
        self.setup_ui()
        
        # Попытка подключения к Ollama
        self.init_ollama()
    
    def setup_ui(self):
        """Создание интерфейса"""
        # Главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Файл меню
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Новый проект", command=self.new_project)
        file_menu.add_command(label="Открыть проект", command=self.open_project)
        file_menu.add_separator()
        file_menu.add_command(label="Сохранить файл", command=self.save_current_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Сохранить как...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit_app)
        
        # Проект меню
        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Проект", menu=project_menu)
        project_menu.add_command(label="📋 Управление проектами", command=self.open_project_manager)
        project_menu.add_command(label="📁 Управление файлами", command=self.open_file_manager)
        project_menu.add_separator()
        project_menu.add_command(label="🔍 Автообнаружение файлов", command=self.auto_discover_files)
        project_menu.add_command(label="📊 Статистика проекта", command=self.show_project_stats)
        
        # Виджет меню
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Показать/Скрыть Нейро", command=self.toggle_neuro_panel)
        
        # Основная панель
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Левая панель (проводник файлов)
        self.left_frame = ttk.Frame(main_paned, width=250)
        main_paned.add(self.left_frame, weight=1)
        
        # Центральная панель (редактор)
        self.center_frame = ttk.Frame(main_paned)
        main_paned.add(self.center_frame, weight=3)
        
        # Правая панель (Нейро)
        self.right_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(self.right_frame, weight=1)
        
        self.setup_file_explorer()
        self.setup_editor()
        self.setup_neuro_panel()
        
        # Статус бар
        self.status_bar = ttk.Label(self.root, text="Готов к работе", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_file_explorer(self):
        """Настройка проводника файлов"""
        # Заголовок
        ttk.Label(self.left_frame, text="Проводник файлов", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Дерево файлов
        self.file_tree = ttk.Treeview(self.left_frame, columns=("size", "type"), show="tree")
        self.file_tree.heading("#0", text="Файлы")
        self.file_tree.column("#0", width=200)
        self.file_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Контекстное меню
        self.file_tree.bind("<Button-3>", self.show_file_context_menu)
        self.file_tree.bind("<Double-1>", self.open_file_in_editor)
        
        # Кнопки управления
        button_frame = ttk.Frame(self.left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Создать файл", command=self.create_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Создать папку", command=self.create_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Обновить", command=self.refresh_file_tree).pack(side=tk.LEFT, padx=2)
    
    def setup_editor(self):
        """Настройка редактора кода"""
        # Заголовок
        ttk.Label(self.center_frame, text="Редактор кода", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Текстовый редактор
        self.editor_frame = ttk.Frame(self.center_frame)
        self.editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем Notebook для редактора и чата
        self.center_notebook = ttk.Notebook(self.editor_frame)
        self.center_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка редактора
        self.editor_tab = ttk.Frame(self.center_notebook)
        self.center_notebook.add(self.editor_tab, text="📝 Редактор")
        
        # Вкладка общего чата
        self.chat_tab = ttk.Frame(self.center_notebook)
        self.center_notebook.add(self.chat_tab, text="💬 Общий чат")
        
        self.setup_editor_tab()
        self.setup_chat_tab()
        
        # Информация о файле
        self.file_info_label = ttk.Label(self.center_frame, text="Файл не открыт")
        self.file_info_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Переменные для отслеживания изменений
        self.current_file = None
        self.file_modified = False
        self.original_content = ""
    
    def setup_editor_tab(self):
        """Настройка вкладки редактора"""
        # Панель инструментов редактора
        toolbar_frame = ttk.Frame(self.editor_tab)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.save_button = ttk.Button(toolbar_frame, text="💾 Сохранить", command=self.save_current_file, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=2)
        
        self.send_file_button = ttk.Button(toolbar_frame, text="📤 Отправить файл", command=self.send_current_file_to_chat)
        self.send_file_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        self.file_path_label = ttk.Label(toolbar_frame, text="Файл не открыт", foreground="gray")
        self.file_path_label.pack(side=tk.LEFT, padx=5)
        
        # Текстовое поле с прокруткой
        text_container = ttk.Frame(self.editor_tab)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        self.editor_text = tk.Text(text_container, wrap=tk.WORD, font=("Consolas", 10), undo=True)
        scrollbar_y = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.editor_text.yview)
        scrollbar_x = ttk.Scrollbar(text_container, orient=tk.HORIZONTAL, command=self.editor_text.xview)
        
        self.editor_text.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        text_container.grid_rowconfigure(0, weight=1)
        text_container.grid_columnconfigure(0, weight=1)
        
        self.editor_text.config(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # Отслеживание изменений
        self.editor_text.bind('<KeyRelease>', self.on_text_changed)
        self.editor_text.bind('<Button-1>', self.on_text_changed)
    
    def setup_chat_tab(self):
        """Настройка вкладки общего чата"""
        # Заголовок
        ttk.Label(self.chat_tab, text="💬 Общий чат проекта", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Кнопки управления чатом
        chat_controls = ttk.Frame(self.chat_tab)
        chat_controls.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(chat_controls, text="🔄 Обновить чат", command=self.refresh_chat).pack(side=tk.LEFT, padx=2)
        ttk.Button(chat_controls, text="🗑️ Очистить чат", command=self.clear_chat).pack(side=tk.LEFT, padx=2)
        ttk.Button(chat_controls, text="📤 Отправить файл в чат", command=self.send_current_file_to_chat).pack(side=tk.LEFT, padx=2)
        
        # Поле для сообщения
        msg_frame = ttk.LabelFrame(self.chat_tab, text="Сообщение")
        msg_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.chat_message = tk.Text(msg_frame, height=3, wrap=tk.WORD)
        self.chat_message.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(msg_frame, text="📨 Отправить сообщение", command=self.send_chat_message).pack(pady=5)
        
        # История чата
        chat_history_frame = ttk.LabelFrame(self.chat_tab, text="История чата")
        chat_history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.chat_history = scrolledtext.ScrolledText(chat_history_frame, height=20, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Автообновление чата каждые 5 секунд
        self.schedule_chat_refresh()
    
    def setup_neuro_panel(self):
        """Настройка панели Нейро"""
        # Заголовок
        ttk.Label(self.right_frame, text="🧠 Нейро", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Статус подключения
        self.neuro_status_label = ttk.Label(self.right_frame, text="Статус: Не подключено", foreground="red")
        self.neuro_status_label.pack(pady=5)
        
        # Чат с нейросетью
        ttk.Label(self.right_frame, text="Вопрос к нейросети:").pack(pady=5)
        
        self.neuro_question = tk.Text(self.right_frame, height=3, wrap=tk.WORD)
        self.neuro_question.pack(fill=tk.X, padx=5, pady=2)
        
        # Кнопки для ввода вопроса
        question_buttons_frame = ttk.Frame(self.right_frame)
        question_buttons_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(question_buttons_frame, text="📝 Отправить вопрос", command=self.ask_neuro).pack(side=tk.LEFT, padx=2)
        
        # Кнопка голосового ввода (улучшенная версия)
        if ADVANCED_VOICE_AVAILABLE:
            self.voice_button = ttk.Button(question_buttons_frame, text="🎤 Голос (реальное время)", command=self.toggle_advanced_voice_input)
            self.voice_button.pack(side=tk.LEFT, padx=2)
            self.is_recording_voice = False
            self.voice_status_label = ttk.Label(question_buttons_frame, text="", foreground="blue")
            self.voice_status_label.pack(side=tk.LEFT, padx=5)
        elif VOICE_AVAILABLE:
            self.voice_button = ttk.Button(question_buttons_frame, text="🎤 Голосовой ввод", command=self.toggle_voice_input)
            self.voice_button.pack(side=tk.LEFT, padx=2)
            self.is_recording_voice = False
        else:
            ttk.Button(question_buttons_frame, text="🎤 Голос (недоступен)", state=tk.DISABLED).pack(side=tk.LEFT, padx=2)
        
        # Ответ нейросети
        ttk.Label(self.right_frame, text="Ответ:").pack(pady=5)
        
        self.neuro_response = tk.Text(self.right_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        self.neuro_response.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # Кнопка обновления контекста
        ttk.Button(self.right_frame, text="Обновить контекст", command=self.update_neuro_context).pack(pady=5)
    
    def init_ollama(self):
        """Инициализация подключения к Ollama"""
        def check_connection():
            self.ollama_manager = OllamaManager()
            if self.ollama_manager.test_connection():
                self.neuro_status_label.config(text="Статус: Подключено", foreground="green")
                self.logger.info("Подключение к Ollama установлено")
            else:
                self.neuro_status_label.config(text="Статус: Ошибка подключения", foreground="red")
                self.logger.error("Не удалось подключиться к Ollama")
        
        threading.Thread(target=check_connection, daemon=True).start()
    
    def init_database(self):
        """Инициализация новой системы баз данных"""
        try:
            # Инициализация логгера
            self.app_logger = AppLogger("context")
            self.app_logger.log_app_start("StartIDE")
            
            # Инициализация базы данных
            self.db_manager = DatabaseManager("context")
            self.app_logger.log_database_action("init", "База данных инициализирована")
            self.logger.info("База данных инициализирована")
            
            # Инициализация менеджеров проектов и файлов
            self.project_manager = ProjectManager("context")
            self.file_tracker = FileTracker("context")
            self.app_logger.log_database_action("init", "Менеджеры проектов и файлов инициализированы")
            
            # Настройка горячих клавиш
            self.setup_hotkeys()
            
            # Инициализация голосового менеджера (опционально)
            if ADVANCED_VOICE_AVAILABLE:
                try:
                    self.advanced_voice_manager = AdvancedVoiceManager()
                    if self.advanced_voice_manager.init_voice_input():
                        self.app_logger.log_voice_action("init", "Улучшенный голосовой ввод инициализирован")
                        self.logger.info("Улучшенный голосовой ввод инициализирован")
                    else:
                        self.app_logger.log_warning("Не удалось инициализировать улучшенный голосовой ввод")
                        self.logger.warning("Не удалось инициализировать улучшенный голосовой ввод")
                except Exception as e:
                    self.app_logger.log_error(f"Ошибка улучшенного голосового ввода: {e}")
                    self.advanced_voice_manager = None
                    self.app_logger.log_warning("Голосовой ввод недоступен (требуется установка speechrecognition)")
                    self.logger.warning("Голосовой ввод недоступен")
            
            # Инициализация голосового менеджера (старый метод)
            try:
                from StartIDE.voice_input_manager import VoiceInputManager
                self.voice_manager = VoiceInputManager()
                self.app_logger.log_voice_action("init", "Голосовой менеджер инициализирован")
            except ImportError:
                self.voice_manager = None
                self.app_logger.log_warning("Голосовой менеджер недоступен")
                
        except Exception as e:
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка инициализации базы данных: {e}")
            self.logger.error(f"Ошибка инициализации базы данных: {e}")
            messagebox.showerror("Ошибка", f"Не удалось инициализировать базу данных: {e}")
    
    def new_project(self):
        """Создание нового проекта"""
        folder_path = filedialog.askdirectory(title="Выберите папку для проекта")
        if folder_path:
            self.project_path = Path(folder_path)
            
            # Инициализация новой системы баз данных
            if self.db_manager:
                self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))
                self.git_manager = GitManager(str(self.project_path), self.db_manager)
                
                # Обновляем Git контекст
                if self.git_manager.is_git_repo:
                    threading.Thread(target=self.git_manager.update_git_context, args=(self.current_project_id,), daemon=True).start()
            
            # Сохраняем старую систему для совместимости
            self.project_context = ProjectContext(str(self.project_path))
            self.shared_chat_manager = SharedChatManager(str(self.project_path))
            self.project_context.update_context("project_created", f"Проект создан в {folder_path}")
            
            self.refresh_file_tree()
            self.status_bar.config(text=f"Проект: {self.project_path.name}")
            
            # Отправляем контекст в нейросеть
            if self.ollama_manager:
                threading.Thread(target=self.send_context_to_neuro, daemon=True).start()
    
    def open_project(self):
        """Открытие существующего проекта автоматически"""
        folder_path = filedialog.askdirectory(title="Выберите папку проекта")
        if folder_path:
            self.project_path = Path(folder_path)
            
            # Проверяем, что это действительно проект
            if not self._is_valid_project_folder(self.project_path):
                result = messagebox.askyesno(
                    "Внимание", 
                    "Выбранная папка не похожа на программный проект. Открыть anyway?"
                )
                if not result:
                    return
            
            # Инициализация новой системы баз данных
            if self.db_manager:
                self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))
                self.git_manager = GitManager(str(self.project_path), self.db_manager)
                
                # Автоанализ проекта в фоне
                from shared.project_auto_analyzer import ProjectAutoAnalyzer
                analyzer = ProjectAutoAnalyzer(self.db_manager)
                
                threading.Thread(
                    target=self._auto_analyze_and_update, 
                    args=(analyzer, str(self.project_path)), 
                    daemon=True
                ).start()
                
                # Обновляем Git контекст
                if self.git_manager.is_git_repo:
                    threading.Thread(target=self.git_manager.update_git_context, args=(self.current_project_id,), daemon=True).start()
            
            # Сохраняем старую систему для совместимости
            self.project_context = ProjectContext(str(self.project_path))
            self.shared_chat_manager = SharedChatManager(str(self.project_path))
            self.project_context.update_context("project_opened", f"Проект открыт: {self.project_path}")
            
            self.refresh_file_tree()
            self.status_bar.config(text=f"Проект: {self.project_path.name} (анализ...)")
            
            # Отправляем контекст в нейросеть
            if self.ollama_manager:
                threading.Thread(target=self.send_context_to_neuro, daemon=True).start()
                
            if self.app_logger:
                self.app_logger.log_project_open(str(self.project_path), self.current_project_id)
    
    def _is_valid_project_folder(self, path: Path) -> bool:
        """Проверка, является ли папка проектом"""
        # Индикаторы проекта
        project_indicators = [
            # Файлы конфигурации
            'package.json', 'requirements.txt', 'setup.py', 'pyproject.toml',
            'pom.xml', 'build.gradle', 'Cargo.toml', 'go.mod', 'composer.json',
            'Gemfile', 'Makefile', 'CMakeLists.txt',
            
            # Основные файлы
            'main.py', 'app.py', 'index.js', 'app.js', 'main.js',
            'index.html', 'index.php', 'main.cpp', 'main.go', 'main.rs',
            
            # Папки проекта
            'src/', 'lib/', 'app/', 'components/', 'models/', 'views/'
        ]
        
        for indicator in project_indicators:
            if indicator.endswith('/'):
                # Проверка папки
                if (path / indicator).exists():
                    return True
            else:
                # Проверка файла
                if (path / indicator).exists():
                    return True
        
        # Проверяем наличие исходных файлов
        code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb']
        for item in path.iterdir():
            if item.is_file() and item.suffix in code_extensions:
                return True
        
        return False
    
    def _auto_analyze_and_update(self, analyzer: 'ProjectAutoAnalyzer', project_path: str):
        """Автоанализ проекта и обновление UI"""
        try:
            # Выполняем анализ
            project_data = analyzer.analyze_project(project_path)
            
            if project_data:
                # Обновляем статус в главном потоке
                self.root.after(0, lambda: self.status_bar.config(text=f"Проект: {project_data['name']}"))
                
                # Обновляем информацию о проекте
                self.root.after(0, lambda: self._update_project_info_display(project_data))
                
                self.logger.info(f"Проанализирован проект: {project_data['name']}")
            else:
                self.root.after(0, lambda: self.status_bar.config(text=f"Проект: {Path(project_path).name}"))
                
        except Exception as e:
            self.logger.error(f"Ошибка автоанализа проекта: {e}")
            self.root.after(0, lambda: self.status_bar.config(text=f"Проект: {Path(project_path).name} (ошибка анализа)"))
    
    def _update_project_info_display(self, project_data: Dict):
        """Обновление отображения информации о проекте"""
        try:
            # Можно добавить отображение информации о проекте в UI
            # Например, в статусной строке или отдельной панели
            
            # Показываем основные технологии в статусе
            tech_stack = project_data.get('tech_stack', {})
            if tech_stack.get('languages'):
                main_lang = tech_stack['languages'][0]['name']
                current_status = self.status_bar.cget("text")
                self.status_bar.config(text=f"{current_status} | {main_lang}")
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления информации о проекте: {e}")
    
    def refresh_file_tree(self):
        """Обновление дерева файлов"""
        if not self.project_path:
            return
        
        # Очищаем дерево
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Добавляем файлы и папки
        try:
            for item in self.project_path.iterdir():
                if item.name.startswith('.'):
                    continue
                    
                if item.is_dir():
                    node = self.file_tree.insert("", "end", text=f"📁 {item.name}", values=("", "folder"))
                    self.add_folder_contents(item, node)
                else:
                    size = f"{item.stat().st_size} байт" if item.stat().st_size < 1024 else f"{item.stat().st_size//1024} КБ"
                    self.file_tree.insert("", "end", text=f"📄 {item.name}", values=(size, "file"))
        except Exception as e:
            self.logger.error(f"Ошибка обновления дерева файлов: {e}")
    
    def add_folder_contents(self, folder_path, parent_node):
        """Рекурсивное добавление содержимого папки"""
        try:
            for item in folder_path.iterdir():
                if item.name.startswith('.'):
                    continue
                    
                if item.is_dir():
                    node = self.file_tree.insert(parent_node, "end", text=f"📁 {item.name}", values=("", "folder"))
                    self.add_folder_contents(item, node)
                else:
                    size = f"{item.stat().st_size} байт" if item.stat().st_size < 1024 else f"{item.stat().st_size//1024} КБ"
                    self.file_tree.insert(parent_node, "end", text=f"📄 {item.name}", values=(size, "file"))
        except Exception as e:
            self.logger.error(f"Ошибка добавления содержимого папки: {e}")
    
    def create_file(self):
        """Создание нового файла"""
        if not self.project_path:
            messagebox.showwarning("Внимание", "Сначала создайте или откройте проект")
            return
        
        file_name = tk.simpledialog.askstring("Создать файл", "Введите имя файла:")
        if file_name:
            try:
                new_file = self.project_path / file_name
                new_file.touch()
                
                if self.project_context:
                    self.project_context.add_file_change(str(new_file), "created")
                
                self.refresh_file_tree()
                self.status_bar.config(text=f"Файл создан: {file_name}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать файл: {e}")
    
    def create_folder(self):
        """Создание новой папки"""
        if not self.project_path:
            messagebox.showwarning("Внимание", "Сначала создайте или откройте проект")
            return
        
        folder_name = tk.simpledialog.askstring("Создать папку", "Введите имя папки:")
        if folder_name:
            try:
                new_folder = self.project_path / folder_name
                new_folder.mkdir()
                
                if self.project_context:
                    self.project_context.add_folder_change(str(new_folder), "created")
                
                self.refresh_file_tree()
                self.status_bar.config(text=f"Папка создана: {folder_name}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать папку: {e}")
    
    def open_file_in_editor(self, event):
        """Открытие файла в редакторе"""
        selection = self.file_tree.selection()
        if selection:
            item = self.file_tree.item(selection[0])
            file_name = item['text'].replace('📁 ', '').replace('📄 ', '')
            
            if item['values'][1] == 'file':
                try:
                    # Сохраняем текущий файл если есть изменения
                    if self.current_file and self.file_modified:
                        result = messagebox.askyesno("Несохраненные изменения", 
                                                   f"Сохранить изменения в файле {self.current_file.name}?")
                        if result:
                            self.save_current_file()
                    
                    file_path = self.project_path / file_name
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Загружаем файл в редактор
                    self.editor_text.delete(1.0, tk.END)
                    self.editor_text.insert(1.0, content)
                    
                    # Обновляем интерфейс
                    self.current_file = file_path
                    self.original_content = content
                    self.file_modified = False
                    self.save_button.config(state=tk.DISABLED)
                    
                    # Обновляем метки
                    self.file_path_label.config(text=f"📄 {file_name}", foreground="black")
                    self.file_info_label.config(text=f"Файл: {file_name} | Размер: {len(content)} символов")
                    self.status_bar.config(text=f"Открыт файл: {file_name}")
                    
                    if self.project_context:
                        self.project_context.add_file_change(str(file_path), "opened")
                        
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
    
    def on_text_changed(self, event=None):
        """Обработка изменений в тексте"""
        if self.current_file and not self.file_modified:
            current_content = self.editor_text.get(1.0, tk.END).strip()
            if current_content != self.original_content.strip():
                self.file_modified = True
                self.save_button.config(state=tk.NORMAL)
                self.file_path_label.config(text=f"📄 {self.current_file.name} *", foreground="red")
                self.status_bar.config(text=f"Файл изменен: {self.current_file.name}")
    
    def on_text_modified(self, event):
        """Обработка события Modified"""
        try:
            self.editor_text.edit_modified(False)
            self.on_text_changed()
        except:
            pass
    
    def save_current_file(self):
        """Сохранение текущего файла"""
        if not self.current_file:
            return
        
        try:
            content = self.editor_text.get(1.0, tk.END).rstrip()
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Обновляем состояние
            self.original_content = content
            self.file_modified = False
            self.save_button.config(state=tk.DISABLED)
            
            # Обновляем интерфейс
            self.file_path_label.config(text=f"📄 {self.current_file.name}", foreground="black")
            self.status_bar.config(text=f"Файл сохранен: {self.current_file.name}")
            
            if self.project_context:
                self.project_context.add_file_change(str(self.current_file), "saved")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
    
    def save_file_as(self):
        """Сохранение файла под новым именем"""
        if not self.current_file:
            return
            
        new_file_path = filedialog.asksaveasfilename(
            title="Сохранить файл как...",
            initialdir=str(self.project_path),
            initialname=self.current_file.name,
            filetypes=[("Текстовые файлы", "*.txt"), ("Python файлы", "*.py"), 
                       ("Все файлы", "*.*")]
        )
        
        if new_file_path:
            try:
                content = self.editor_text.get(1.0, tk.END).rstrip()
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Обновляем текущий файл
                self.current_file = Path(new_file_path)
                self.original_content = content
                self.file_modified = False
                self.save_button.config(state=tk.DISABLED)
                
                # Обновляем интерфейс
                self.file_path_label.config(text=f"📄 {self.current_file.name}", foreground="black")
                self.file_info_label.config(text=f"Файл: {self.current_file.name} | Размер: {len(content)} символов")
                self.status_bar.config(text=f"Файл сохранен как: {self.current_file.name}")
                
                # Обновляем дерево файлов
                self.refresh_file_tree()
                
                if self.project_context:
                    self.project_context.add_file_change(str(self.current_file), "saved_as")
                    
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
    
    def show_file_context_menu(self, event):
        """Показ контекстного меню для файлов"""
        pass
    
    def toggle_neuro_panel(self):
        """Переключение видимости панели Нейро"""
        if self.right_frame.winfo_viewable():
            self.right_frame.pack_forget()
        else:
            self.right_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
    
    def ask_neuro(self):
        """Задать вопрос нейросети"""
        if not self.ollama_manager or not self.project_path:
            messagebox.showwarning("Внимание", "Нейросеть не доступна или проект не открыт")
            return
        
        question = self.neuro_question.get(1.0, tk.END).strip()
        if not question:
            return
        
        def get_response():
            response = self.ollama_manager.ask_about_project(question, str(self.project_path))
            
            self.neuro_response.config(state=tk.NORMAL)
            self.neuro_response.delete(1.0, tk.END)
            self.neuro_response.insert(1.0, f"Вопрос: {question}\n\nОтвет: {response}")
            self.neuro_response.config(state=tk.DISABLED)
        
        threading.Thread(target=get_response, daemon=True).start()
    
    def update_neuro_context(self):
        """Обновление контекста нейросети"""
        if not self.ollama_manager or not self.project_context:
            messagebox.showwarning("Внимание", "Нейросеть не доступна")
            return
        
        threading.Thread(target=self.send_context_to_neuro, daemon=True).start()
    
    def send_context_to_neuro(self):
        """Отправка контекста в нейросеть"""
        try:
            context_data = self.project_context.load_context()
            success = self.ollama_manager.send_project_context(str(self.project_path), context_data)
            
            if success:
                self.status_bar.config(text="Контекст отправлен в нейросеть")
            else:
                self.status_bar.config(text="Ошибка отправки контекста")
        except Exception as e:
            self.logger.error(f"Ошибка отправки контекста: {e}")
    
    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С ОБЩИМ ЧАТОМ =====
    
    def refresh_chat(self):
        """Обновление истории чата"""
        if not self.shared_chat_manager:
            return
        
        try:
            messages = self.shared_chat_manager.get_messages_since(self.last_chat_timestamp)
            
            if messages:
                self.chat_history.config(state=tk.NORMAL)
                
                for msg in messages:
                    timestamp = msg.get("timestamp", "")[11:19]
                    sender = msg.get("sender", "Unknown")
                    msg_type = msg.get("type", "text")
                    content = msg.get("content", "")
                    file_name = msg.get("file_name", "")
                    
                    # Форматируем сообщение
                    if msg_type == "file" or msg_type == "code_analysis":
                        self.chat_history.insert(tk.END, f"[{timestamp}] {sender} отправил файл:\n")
                        if file_name:
                            self.chat_history.insert(tk.END, f"  📄 {file_name}\n")
                        if content:
                            self.chat_history.insert(tk.END, f"  💬 {content}\n")
                    else:
                        self.chat_history.insert(tk.END, f"[{timestamp}] {sender}:\n")
                        self.chat_history.insert(tk.END, f"  💬 {content}\n")
                    
                    self.chat_history.insert(tk.END, "-" * 50 + "\n")
                    
                    # Обновляем последний таймстамп
                    if msg.get("timestamp", "") > (self.last_chat_timestamp or ""):
                        self.last_chat_timestamp = msg.get("timestamp")
                
                self.chat_history.see(tk.END)  # Прокручиваем к последнему сообщению
                self.chat_history.config(state=tk.DISABLED)
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления чата: {e}")
    
    def clear_chat(self):
        """Очистка чата"""
        if not self.shared_chat_manager:
            return
        
        if messagebox.askyesno("Подтверждение", "Очистить историю чата?"):
            self.shared_chat_manager.clear_chat()
            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.delete(1.0, tk.END)
            self.chat_history.config(state=tk.DISABLED)
            self.last_chat_timestamp = None
            self.status_bar.config(text="Чат очищен")
    
    def send_chat_message(self):
        """Отправка текстового сообщения в чат"""
        if not self.shared_chat_manager:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return
        
        message = self.chat_message.get(1.0, tk.END).strip()
        if not message:
            return
        
        # Отправка в старую систему (для совместимости)
        success = self.shared_chat_manager.add_message(
            sender="StartIDE",
            message_type="text",
            content=message
        )
        
        # Отправка в новую базу данных
        if self.db_manager and self.current_project_id:
            try:
                self.db_manager.add_chat_message(
                    self.current_project_id,
                    "StartIDE",
                    "text",
                    message
                )
            except Exception as e:
                self.logger.error(f"Ошибка сохранения в БД: {e}")
        
        if success:
            self.chat_message.delete(1.0, tk.END)
            self.refresh_chat()
            self.status_bar.config(text="Сообщение отправлено в чат")
        else:
            messagebox.showerror("Ошибка", "Не удалось отправить сообщение")
    
    def send_current_file_to_chat(self):
        """Отправка текущего файла в чат"""
        if not self.shared_chat_manager:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return
        
        if not self.current_file:
            messagebox.showwarning("Внимание", "Сначала откройте файл")
            return
        
        try:
            # Читаем содержимое файла
            with open(self.current_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Спрашиваем вопрос для анализа
            question = tk.simpledialog.askstring(
                "Отправка файла в чат",
                "Введите вопрос или комментарий к файлу:",
                initialvalue="Проанализируй этот файл"
            )
            
            if question is None:  # Пользователь отменил
                return
            
            # Отправляем в чат
            success = self.shared_chat_manager.send_file_for_analysis(
                sender="StartIDE",
                file_path=str(self.current_file),
                question=question
            )
            
            if success:
                self.refresh_chat()
                self.status_bar.config(text=f"Файл {self.current_file.name} отправлен в чат")
                
                # Переключаемся на вкладку чата
                self.center_notebook.select(self.chat_tab)
            else:
                messagebox.showerror("Ошибка", "Не удалось отправить файл")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить файл: {e}")
    
    def schedule_chat_refresh(self):
        """Планирование автоматического обновления чата"""
        if self.project_path:
            self.refresh_chat()
        
        # Планируем следующее обновление через 5 секунд
        self.root.after(5000, self.schedule_chat_refresh)
    
    def toggle_advanced_voice_input(self):
        """Переключение улучшенного голосового ввода с реальным временем"""
        if not ADVANCED_VOICE_AVAILABLE or not self.advanced_voice_manager:
            messagebox.showwarning("Голосовой ввод", "Улучшенный голосовой ввод недоступен. Установите speechrecognition.")
            return
        
        if not self.is_recording_voice:
            # Начинаем непрерывную запись
            self.voice_button.config(text="⏹️ Остановить запись")
            self.is_recording_voice = True
            
            # Настраиваем чувствительность для русского языка
            self.advanced_voice_manager.set_language("ru-RU")
            self.advanced_voice_manager.set_sensitivity(0.7)
            
            # Устанавливаем callback для частичного распознавания в реальном времени
            def partial_callback(text):
                # Показываем распознаваемый текст в статусе
                if hasattr(self, 'voice_status_label'):
                    self.voice_status_label.config(text=f"🗣️: {text}")
                
                # Умная логика вставки текста без затирания предыдущего
                current_text = self.neuro_question.get(1.0, tk.END).strip()
                text_to_add = text.strip()
                
                if not text_to_add:
                    return
                
                if not current_text:
                    # Если поле пустое, добавляем первое слово
                    self.neuro_question.insert(tk.END, text_to_add + " ")
                else:
                    # Проверяем, заканчивается ли текущий текст на неполное слово
                    words = current_text.split()
                    if words:
                        last_word = words[-1]
                        
                        # Если последнее слово короче 3 символов или похоже на текущее распознавание
                        if len(last_word) <= 3 or (text_to_add.lower().startswith(last_word.lower()) and len(text_to_add) > len(last_word)):
                            # Заменяем последнее слово на более полное
                            words[-1] = text_to_add
                            new_text = " ".join(words) + " "
                            
                            # Обновляем только последние символы
                            self.neuro_question.delete(1.0, tk.END)
                            self.neuro_question.insert(1.0, new_text)
                        else:
                            # Добавляем новое слово
                            self.neuro_question.insert(tk.END, text_to_add + " ")
                    else:
                        # Добавляем как новое слово
                        self.neuro_question.insert(tk.END, text_to_add + " ")
                
                self.neuro_question.see(tk.END)
            
            # Устанавливаем callback для финального текста
            def final_callback(text):
                if text.strip():
                    # Обновляем статус
                    if hasattr(self, 'voice_status_label'):
                        self.voice_status_label.config(text=f"✅: {text[:30]}...")
            
            self.advanced_voice_manager.set_partial_text_callback(partial_callback)
            self.advanced_voice_manager.set_text_callback(final_callback)
            
            # Начинаем непрерывную запись
            self.advanced_voice_manager.start_continuous_recording(self.neuro_question)
            
            if self.app_logger:
                self.app_logger.log_voice_action("start", "Начат улучшенный голосовой ввод (реальное время)")
            
            self.status_bar.config(text="🎤 Голосовой ввод (реальное время)...")
        else:
            # Останавливаем запись
            self.voice_button.config(text="🎤 Голос (реальное время)")
            self.is_recording_voice = False
            
            final_text = self.advanced_voice_manager.stop_recording()
            
            # Обновляем статус
            if hasattr(self, 'voice_status_label'):
                self.voice_status_label.config(text=f"✅ Готово")
            
            if self.app_logger:
                self.app_logger.log_voice_action("stop", f"Завершен улучшенный голосовой ввод: {final_text[:50]}...")
            
            self.status_bar.config(text="Готов к работе")
    
    def toggle_voice_input(self):
        """Переключение базового голосового ввода"""
        if not VOICE_AVAILABLE or not self.voice_manager:
            messagebox.showwarning("Голосовой ввод", "Голосовой ввод недоступен. Установите speechrecognition.")
            return
        
        if not self.is_recording_voice:
            # Начинаем запись
            self.voice_button.config(text="⏹️ Остановить запись", style="Accent.TButton")
            self.is_recording_voice = True
            
            # Устанавливаем callback для обработки распознанного текста
            def voice_callback(text):
                # Вставляем распознанный текст в поле вопроса
                self.neuro_question.insert(tk.END, text + " ")
                self.neuro_question.see(tk.END)
            
            self.voice_manager.set_text_callback(voice_callback)
            self.voice_manager.start_recording()
            
            if self.app_logger:
                self.app_logger.log_voice_action("start", "Начат голосовой ввод вопроса")
            
            self.status_bar.config(text="🎤 Голосовая запись...")
        else:
            # Останавливаем запись
            self.voice_button.config(text="🎤 Голосовой ввод")
            self.is_recording_voice = False
            
            recognized_text = self.voice_manager.stop_recording()
            
            if self.app_logger:
                self.app_logger.log_voice_action("stop", f"Распознано: {recognized_text[:50]}...")
            
            self.status_bar.config(text="Готов к работе")
    
    def open_project_manager(self):
        """Открыть окно управления проектами"""
        try:
            if not self.db_manager:
                messagebox.showerror("Ошибка", "База данных не инициализирована")
                return
            
            ProjectManagerWindow(self.root, self.db_manager, self.app_logger)
            
            if self.app_logger:
                self.app_logger.log_ui_action("open_project_manager", "Открыто окно управления проектами")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть управление проектами: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка открытия управления проектами: {e}")
    
    def open_file_manager(self):
        """Открыть управление файлами текущего проекта"""
        # Проверяем и устанавливаем current_project_id если нужно
        if not self.current_project_id and self.project_path and self.db_manager:
            self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))
        
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return
        
        try:
            # Создаем простое окно управления файлами
            file_window = tk.Toplevel(self.root)
            file_window.title("Управление файлами")
            file_window.geometry("800x600")
            file_window.transient(self.root)
            
            # Получаем файлы проекта
            files = self.file_tracker.get_tracked_files(self.current_project_id)
            
            # Создаем интерфейс
            ttk.Label(file_window, text=f"Файлы проекта (ID: {self.current_project_id})", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Дерево файлов
            columns = ("file_path", "description", "tags", "updated")
            files_tree = ttk.Treeview(file_window, columns=columns, show="tree headings")
            files_tree.heading("#0", text="ID")
            files_tree.heading("file_path", text="Файл")
            files_tree.heading("description", text="Описание")
            files_tree.heading("tags", text="Теги")
            files_tree.heading("updated", text="Обновлен")
            
            files_tree.column("#0", width=50)
            files_tree.column("file_path", width=250)
            files_tree.column("description", width=150)
            files_tree.column("tags", width=100)
            files_tree.column("updated", width=120)
            
            # Добавляем файлы
            for file_info in files:
                tags_str = ', '.join(file_info.get('tags', []))
                files_tree.insert("", "end", text=str(file_info['id']),
                               values=(file_info['file_path'], 
                                      file_info.get('description', ''),
                                      tags_str,
                                      file_info['updated_at'][:16] if file_info['updated_at'] else ""))
            
            files_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Кнопки
            button_frame = ttk.Frame(file_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Button(button_frame, text="🔍 Автообнаружение", 
                      command=lambda: self.auto_discover_files_for_window(file_window)).pack(side=tk.LEFT, padx=2)
            ttk.Button(button_frame, text="🔄 Обновить", 
                      command=lambda: self.refresh_files_for_window(file_window)).pack(side=tk.LEFT, padx=2)
            ttk.Button(button_frame, text="Закрыть", 
                      command=file_window.destroy).pack(side=tk.RIGHT, padx=2)
            
            if self.app_logger:
                self.app_logger.log_ui_action("open_file_manager", f"Проект {self.current_project_id}")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть управление файлами: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка открытия управления файлами: {e}")
    
    def auto_discover_files(self):
        """Автообнаружение файлов для текущего проекта"""
        # Проверяем и устанавливаем current_project_id если нужно
        if not self.current_project_id and self.project_path and self.db_manager:
            self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))
        
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return
        
        try:
            count = self.file_tracker.auto_discover_files(self.current_project_id)
            messagebox.showinfo("Успех", f"Обнаружено {count} файлов")
            
            if self.app_logger:
                self.app_logger.log_ui_action("auto_discover_files", f"Проект {self.current_project_id}, файлов: {count}")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка автообнаружения файлов: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка автообнаружения файлов: {e}")
    
    def auto_discover_files_for_window(self, window):
        """Автообнаружение файлов для окна"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return
        
        try:
            count = self.file_tracker.auto_discover_files(self.current_project_id)
            messagebox.showinfo("Успех", f"Обнаружено {count} файлов")
            
            # Обновляем окно
            window.destroy()
            self.open_file_manager()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка автообнаружения файлов: {e}")
    
    def refresh_files_for_window(self, window):
        """Обновление файлов для окна"""
        window.destroy()
        self.open_file_manager()
    
    def show_project_stats(self):
        """Показать статистику проекта"""
        # Проверяем и устанавливаем current_project_id если нужно
        if not self.current_project_id and self.project_path and self.db_manager:
            self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))
        
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return
        
        try:
            project_stats = self.project_manager.get_project_stats(self.current_project_id)
            file_stats = self.file_tracker.get_file_stats(self.current_project_id)
            
            stats_text = "=== СТАТИСТИКА ПРОЕКТА ===\n\n"
            stats_text += f"ID проекта: {self.current_project_id}\n"
            stats_text += f"Отслеживаемых файлов: {project_stats.get('tracked_files', 0)}\n"
            stats_text += f"Сообщений в чате: {project_stats.get('chat_messages', 0)}\n"
            stats_text += f"Git коммитов: {project_stats.get('git_commits', 0)}\n"
            stats_text += f"Размер контекста: {project_stats.get('context_size', 0)} байт\n\n"
            
            stats_text += "=== СТАТИСТИКА ФАЙЛОВ ===\n\n"
            stats_text += f"Всего файлов: {file_stats.get('total_files', 0)}\n"
            stats_text += f"Общий размер: {file_stats.get('total_size', 0)} байт\n\n"
            
            if file_stats.get('extensions'):
                stats_text += "Расширения:\n"
                for ext, count in file_stats['extensions'].items():
                    stats_text += f"  {ext}: {count}\n"
            
            # Показываем в отдельном окне
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Статистика проекта")
            stats_window.geometry("400x500")
            
            from tkinter import scrolledtext
            text_widget = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(1.0, stats_text)
            text_widget.config(state=tk.DISABLED)
            
            if self.app_logger:
                self.app_logger.log_ui_action("show_project_stats", f"Проект {self.current_project_id}")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка получения статистики: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка получения статистики: {e}")
    
    def open_project_by_path(self, project_path):
        """Открыть проект по пути"""
        try:
            self.project_path = Path(project_path)
            
            # Инициализация новой системы баз данных
            if self.db_manager:
                self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))
                self.git_manager = GitManager(str(self.project_path), self.db_manager)
                
                # Обновляем Git контекст
                if self.git_manager.is_git_repo:
                    threading.Thread(target=self.git_manager.update_git_context, args=(self.current_project_id,), daemon=True).start()
            
            # Сохраняем старую систему для совместимости
            self.project_context = ProjectContext(str(self.project_path))
            self.shared_chat_manager = SharedChatManager(str(self.project_path))
            self.project_context.update_context("project_created", f"Проект открыт в {project_path}")
            
            self.refresh_file_tree()
            self.status_bar.config(text=f"Проект: {self.project_path.name}")
            
            # Отправляем контекст в нейросеть
            if self.ollama_manager:
                threading.Thread(target=self.send_context_to_neuro, daemon=True).start()
                
            if self.app_logger:
                self.app_logger.log_project_open(str(self.project_path), self.current_project_id)
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть проект: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка открытия проекта: {e}")
    
    def quit_app(self):
        """Выход из приложения"""
        if self.current_file and self.file_modified:
            result = messagebox.askyesno("Несохраненные изменения", 
                                       f"Сохранить изменения в файле {self.current_file.name} перед выходом?")
            if result:
                self.save_current_file()
        
        # Закрытие ресурсов
        if self.db_manager:
            self.db_manager.close()
        if self.voice_manager:
            self.voice_manager.cleanup()
        if self.advanced_voice_manager:
            self.advanced_voice_manager.cleanup()
        
        self.root.quit()
        self.root.destroy()

    def setup_hotkeys(self):
        """Настройка горячих клавиш"""
        # Control + a - выделить весь текст в активном виджете
        self.root.bind('<Control-a>', self.select_all_text)
        
        # Control + m - использовать микрофон
        self.root.bind('<Control-m>', self.toggle_microphone_hotkey)
        
        # Control + y - вернуть текст вперед (redo)
        self.root.bind('<Control-y>', self.redo_text)
        
        # Control + z - вернуть текст назад (undo)
        self.root.bind('<Control-z>', self.undo_text)
        
        # Control + c - копировать текст
        self.root.bind('<Control-c>', self.copy_text)
        
        # Control + v - вставить текст
        self.root.bind('<Control-v>', self.paste_text)
        
        # Win + v - выбрать текст из буфера
        self.root.bind('<Control-v>', self.paste_text)  # Заменяем Win+v на Ctrl+v для совместимости
        
        # Control + s - сохранить файл
        self.root.bind('<Control-s>', lambda e: self.save_current_file())
    
    def select_all_text(self, event):
        """Выделить весь текст в активном виджете"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'tag_add') and hasattr(widget, 'get'):
                widget.tag_add(tk.SEL, "1.0", tk.END)
                widget.mark_set(tk.INSERT, "1.0")
                widget.see(tk.INSERT)
                return "break"
        except:
            pass
        return None
    
    def toggle_microphone_hotkey(self, event):
        """Переключить микрофон по горячей клавише"""
        try:
            # Проверяем, какой виджет в фокусе
            widget = self.root.focus_get()
            if hasattr(widget, 'get') and widget == getattr(self, 'chat_input', None):
                # Если в фокусе чат, используем голосовой ввод для чата
                if ADVANCED_VOICE_AVAILABLE and self.advanced_voice_manager:
                    self.toggle_voice_input()
                elif self.voice_manager:
                    self.toggle_voice_input()
            elif hasattr(widget, 'get') and widget == getattr(self, 'editor', None):
                # Если в фокусе редактор кода, можно добавить голосовой ввод для редактора
                pass  # Можно реализовать позже
            return "break"
        except:
            pass
        return None
    
    def redo_text(self, event):
        """Вернуть текст вперед (redo)"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'edit_redo'):
                widget.edit_redo()
                return "break"
        except:
            pass
        return None
    
    def undo_text(self, event):
        """Вернуть текст назад (undo)"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'edit_undo'):
                widget.edit_undo()
                return "break"
        except:
            pass
        return None
    
    def copy_text(self, event):
        """Копировать текст"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'get') and hasattr(widget, 'tag_ranges'):
                try:
                    text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                    return "break"
                except tk.TclError:
                    # Если нет выделения, копируем весь текст
                    text = widget.get("1.0", tk.END)
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
                    return "break"
        except:
            pass
        return None
    
    def paste_text(self, event):
        """Вставить текст"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'insert'):
                try:
                    text = self.root.clipboard_get()
                    widget.insert(tk.INSERT, text)
                    return "break"
                except tk.TclError:
                    pass
        except:
            pass
        return None
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

if __name__ == "__main__":
    app = StartIDE()
    app.run()
