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

# Опциональный импорт голосового менеджера для документов
try:
    from StartOffice.voice_input_manager import VoiceInputManager
    from StartOffice.advanced_voice_input_manager import AdvancedVoiceInputManager
    VOICE_INPUT_AVAILABLE = True
    ADVANCED_VOICE_INPUT_AVAILABLE = True
except ImportError:
    VOICE_INPUT_AVAILABLE = False
    ADVANCED_VOICE_INPUT_AVAILABLE = False
    VoiceInputManager = None
    AdvancedVoiceInputManager = None

class StartOffice:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Start Office")
        self.root.geometry("1200x800")
        
        # Переменные
        self.ollama_manager = None
        self.projects = []
        
        # Новая система баз данных
        self.db_manager = None
        self.git_manager = None
        self.current_project_id = None
        
        # Голосовой менеджер для документов
        self.voice_input_manager = None
        self.advanced_voice_input_manager = None
        
        # Управление проектами и файлами
        self.project_manager = None
        self.file_tracker = None
        
        # Разделенное логирование
        self.app_logger = None
        
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Инициализация новой системы баз данных
        self.init_database()
        
        # Попытка подключения к Ollama
        self.init_ollama()
        
        # Настройка горячих клавиш
        self.setup_hotkeys()
        
        # Создание интерфейса
        self.setup_ui()
        
        # Поиск проектов (после создания UI)
        self.discover_projects()
    
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
        file_menu.add_command(label="Выход", command=self.quit_app)
        
        # Проект меню
        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Проект", menu=project_menu)
        project_menu.add_command(label="📋 Управление проектами", command=self.open_project_manager)
        project_menu.add_command(label="📁 Управление файлами", command=self.open_file_manager)
        project_menu.add_separator()
        project_menu.add_command(label="🔍 Автообнаружение файлов", command=self.auto_discover_files)
        project_menu.add_command(label="📊 Статистика проекта", command=self.show_project_stats)
        
        # Основная панель
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Левая панель (список проектов)
        self.left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(self.left_frame, weight=1)
        
        # Правая панель (детали проекта и AI ассистент)
        self.right_frame = ttk.Frame(main_paned)
        main_paned.add(self.right_frame, weight=2)
        
        self.setup_project_list()
        self.setup_project_details()
        
        # Статус бар
        self.status_bar = ttk.Label(self.root, text="Готов к работе", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_project_list(self):
        """Настройка списка проектов"""
        # Заголовок
        ttk.Label(self.left_frame, text="📁 Проекты", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Список проектов
        self.project_listbox = tk.Listbox(self.left_frame, font=("Arial", 10))
        self.project_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.project_listbox.bind('<<ListboxSelect>>', self.on_project_select)
        
        # Кнопки управления
        button_frame = ttk.Frame(self.left_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Добавить", command=self.add_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Обновить", command=self.discover_projects).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Удалить", command=self.remove_project).pack(side=tk.LEFT, padx=2)
    
    def setup_project_details(self):
        """Настройка деталей проекта и AI ассистента"""
        # Создаем notebook для вкладок
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладка "Обзор проекта"
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="Обзор проекта")
        self.setup_overview_tab()
        
        # Вкладка "AI Ассистент"
        self.ai_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ai_frame, text="🧠 AI Ассистент")
        self.setup_ai_assistant_tab()
        
        # Вкладка "Общий чат"
        self.chat_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.chat_frame, text="💬 Общий чат")
        self.setup_chat_tab()
        
        # Вкладка "Документ"
        self.document_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.document_frame, text="📄 Документ")
        self.setup_document_tab()
        
        # Вкладка "Структура"
        self.structure_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.structure_frame, text="Структура")
        self.setup_structure_tab()
    
    def setup_overview_tab(self):
        """Настройка вкладки обзора проекта"""
        # Информация о проекте
        info_frame = ttk.LabelFrame(self.overview_frame, text="Информация о проекте")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.project_name_label = ttk.Label(info_frame, text="Проект не выбран", font=("Arial", 10, "bold"))
        self.project_name_label.pack(anchor=tk.W, padx=10, pady=5)
        
        self.project_path_label = ttk.Label(info_frame, text="Путь: -")
        self.project_path_label.pack(anchor=tk.W, padx=10, pady=2)
        
        self.project_files_label = ttk.Label(info_frame, text="Файлов: -")
        self.project_files_label.pack(anchor=tk.W, padx=10, pady=2)
        
        self.project_folders_label = ttk.Label(info_frame, text="Папок: -")
        self.project_folders_label.pack(anchor=tk.W, padx=10, pady=2)
        
        # Последние изменения
        history_frame = ttk.LabelFrame(self.overview_frame, text="Последние изменения")
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.history_text = scrolledtext.ScrolledText(history_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        self.history_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def setup_ai_assistant_tab(self):
        """Настройка вкладки AI ассистента"""
        # Статус подключения
        self.ai_status_label = ttk.Label(self.ai_frame, text="Статус: Не подключено", foreground="red")
        self.ai_status_label.pack(pady=10)
        
        # Выбор поточности данных (куда отправлять/получать от AI)
        flow_frame = ttk.LabelFrame(self.ai_frame, text="🔗 Поточность данных")
        flow_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.flow_mode = tk.StringVar(value="both")
        
        flow_buttons_frame = ttk.Frame(flow_frame)
        flow_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.ide_button = ttk.Radiobutton(flow_buttons_frame, text="Только IDE", 
                                           variable=self.flow_mode, value="ide",
                                           command=self.on_flow_mode_changed)
        self.ide_button.pack(side=tk.LEFT, padx=5)
        
        self.office_button = ttk.Radiobutton(flow_buttons_frame, text="Только Office", 
                                            variable=self.flow_mode, value="office",
                                            command=self.on_flow_mode_changed)
        self.office_button.pack(side=tk.LEFT, padx=5)
        
        self.both_button = ttk.Radiobutton(flow_buttons_frame, text="IDE + Office", 
                                          variable=self.flow_mode, value="both",
                                          command=self.on_flow_mode_changed)
        self.both_button.pack(side=tk.LEFT, padx=5)
        
        self.flow_status_label = ttk.Label(flow_frame, text="Текущий режим: IDE + Office", 
                                          foreground="blue", font=("Arial", 9, "italic"))
        self.flow_status_label.pack(pady=2)
        
        # Выбор .txt файла для работы
        file_frame = ttk.LabelFrame(self.ai_frame, text="Выбор .txt файла для анализа")
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.txt_file_label = ttk.Label(file_frame, text="Файл не выбран", foreground="gray")
        self.txt_file_label.pack(anchor=tk.W, padx=10, pady=5)
        
        file_button_frame = ttk.Frame(file_frame)
        file_button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(file_button_frame, text="Выбрать .txt файл", command=self.select_txt_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_button_frame, text="Обновить", command=self.refresh_txt_file).pack(side=tk.LEFT, padx=2)
        
        # Текстовое поле для просмотра содержимого .txt файла
        txt_content_frame = ttk.LabelFrame(self.ai_frame, text="Содержимое .txt файла")
        txt_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Добавляем кнопки для управления файлом
        button_frame = ttk.Frame(txt_content_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(button_frame, text="💾 Сохранить изменения", command=self.save_txt_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Очистить", command=self.clear_txt_content).pack(side=tk.RIGHT, padx=2)
        
        self.txt_content = scrolledtext.ScrolledText(txt_content_frame, height=10, wrap=tk.WORD, font=("Consolas", 9))
        self.txt_content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Отслеживание изменений в .txt файле
        self.txt_content.bind('<KeyRelease>', self.on_txt_content_changed)
        self.txt_content.bind('<Button-1>', self.on_txt_content_changed)
        
        # Переменные для отслеживания изменений
        self.txt_file_modified = False
        self.original_txt_content = ""
        
        # Вопрос к AI
        question_frame = ttk.LabelFrame(self.ai_frame, text="Задать вопрос о файле")
        question_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(question_frame, text="Вопрос:").pack(anchor=tk.W, padx=10, pady=5)
        
        self.ai_question = tk.Text(question_frame, height=3, wrap=tk.WORD)
        self.ai_question.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(question_frame, text="Отправить вопрос", command=self.ask_ai_about_file).pack(pady=10)
        
        # Ответ AI
        response_frame = ttk.LabelFrame(self.ai_frame, text="Ответ AI")
        response_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.ai_response = scrolledtext.ScrolledText(response_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        self.ai_response.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопка обновления контекста
        ttk.Button(self.ai_frame, text="Обновить контекст проекта", command=self.update_project_context).pack(pady=10)
        
        # Переменные для работы с .txt файлом
        self.current_txt_file = None
        self.txt_file_content = ""
        self.txt_file_modified = False
        self.original_txt_content = ""
        
        # Переменные для общего чата
        self.shared_chat_manager = None
        self.last_chat_timestamp = None
    
    def setup_chat_tab(self):
        """Настройка вкладки общего чата"""
        # Заголовок
        ttk.Label(self.chat_frame, text="💬 Общий чат проекта", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Кнопки управления чатом
        chat_controls = ttk.Frame(self.chat_frame)
        chat_controls.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(chat_controls, text="🔄 Обновить чат", command=self.refresh_chat).pack(side=tk.LEFT, padx=2)
        ttk.Button(chat_controls, text="🗑️ Очистить чат", command=self.clear_chat).pack(side=tk.LEFT, padx=2)
        ttk.Button(chat_controls, text="📤 Отправить файл", command=self.send_file_to_chat).pack(side=tk.LEFT, padx=2)
        
        # Поле для сообщения
        msg_frame = ttk.LabelFrame(self.chat_frame, text="Сообщение")
        msg_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.chat_message = tk.Text(msg_frame, height=3, wrap=tk.WORD)
        self.chat_message.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(msg_frame, text="📨 Отправить сообщение", command=self.send_chat_message).pack(pady=5)
        
        # История чата
        chat_history_frame = ttk.LabelFrame(self.chat_frame, text="История чата")
        chat_history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.chat_history = scrolledtext.ScrolledText(chat_history_frame, height=20, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Автообновление чата
        self.schedule_chat_refresh()
    
    def setup_structure_tab(self):
        """Настройка вкладки структуры проекта"""
        # Дерево файлов
        self.structure_tree = ttk.Treeview(self.structure_frame, columns=("size", "type"), show="tree")
        self.structure_tree.heading("#0", text="Файлы и папки")
        self.structure_tree.column("#0", width=300)
        self.structure_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Полосы прокрутки
        scrollbar_y = ttk.Scrollbar(self.structure_frame, orient=tk.VERTICAL, command=self.structure_tree.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.structure_tree.config(yscrollcommand=scrollbar_y.set)
    
    def init_ollama(self):
        """Инициализация подключения к Ollama"""
        def check_connection():
            self.ollama_manager = OllamaManager()
            if self.ollama_manager.test_connection():
                self.ai_status_label.config(text="Статус: Подключено", foreground="green")
                self.logger.info("Подключение к Ollama установлено")
            else:
                self.ai_status_label.config(text="Статус: Ошибка подключения", foreground="red")
                self.logger.error("Не удалось подключиться к Ollama")
        
        threading.Thread(target=check_connection, daemon=True).start()
    
    def init_database(self):
        """Инициализация новой системы баз данных"""
        try:
            # Инициализация логгера
            self.app_logger = AppLogger("context")
            self.app_logger.log_app_start("StartOffice")
            
            # Инициализация базы данных
            self.db_manager = DatabaseManager("context")
            self.app_logger.log_database_action("init", "База данных инициализирована")
            self.logger.info("База данных инициализирована")
            
            # Инициализация менеджеров проектов и файлов
            self.project_manager = ProjectManager("context")
            self.file_tracker = FileTracker("context")
            self.app_logger.log_database_action("init", "Менеджеры проектов и файлов инициализированы")
            
            # Инициализация голосового менеджера для документов (опционально)
            if ADVANCED_VOICE_INPUT_AVAILABLE:
                try:
                    self.advanced_voice_input_manager = AdvancedVoiceInputManager()
                    if self.advanced_voice_input_manager.init_voice_input():
                        self.app_logger.log_voice_action("init", "Улучшенный голосовой ввод для документов инициализирован")
                        self.logger.info("Улучшенный голосовой ввод для документов инициализирован")
                    else:
                        self.app_logger.log_warning("Не удалось инициализировать улучшенный голосовой ввод для документов")
                        self.logger.warning("Не удалось инициализировать улучшенный голосовой ввод для документов")
                except Exception as e:
                    self.app_logger.log_error(f"Ошибка улучшенного голосового ввода для документов: {e}")
                    self.advanced_voice_input_manager = None
            elif VOICE_INPUT_AVAILABLE:
                self.voice_input_manager = VoiceInputManager()
                if self.voice_input_manager.init_voice_input():
                    self.app_logger.log_voice_action("init", "Базовый голосовой ввод для документов инициализирован")
                    self.logger.info("Базовый голосовой ввод для документов инициализирован")
                else:
                    self.app_logger.log_warning("Не удалось инициализировать базовый голосовой ввод для документов")
                    self.logger.warning("Не удалось инициализировать базовый голосовой ввод для документов")
            else:
                self.voice_input_manager = None
                self.advanced_voice_input_manager = None
                self.app_logger.log_warning("Голосовой ввод для документов недоступен (требуется установка speechrecognition)")
                self.logger.warning("Голосовой ввод для документов недоступен")
                
        except Exception as e:
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка инициализации базы данных: {e}")
            self.logger.error(f"Ошибка инициализации базы данных: {e}")
            messagebox.showerror("Ошибка", f"Не удалось инициализировать базу данных: {e}")
    
    def discover_projects(self):
        """Поиск проектов в текущей директории"""
        self.projects = []
        self.project_listbox.delete(0, tk.END)
        
        current_dir = Path(__file__).parent.parent
        
        for item in current_dir.iterdir():
            if item.is_dir() and (item / ".project_context.json").exists():
                self.projects.append(str(item))
                self.project_listbox.insert(tk.END, item.name)
        
        self.status_bar.config(text=f"Найдено проектов: {len(self.projects)}")
    
    def new_project(self):
        """Создание нового проекта"""
        try:
            if not self.db_manager:
                messagebox.showerror("Ошибка", "База данных не инициализирована")
                return
            
            # Диалог создания проекта
            from StartIDE.project_manager_window import ProjectDialog
            dialog = ProjectDialog(self.root, "Создание проекта")
            
            if dialog.result:
                project_id = self.db_manager.create_project(**dialog.result)
                if project_id:
                    self.discover_projects()
                    messagebox.showinfo("Успех", f"Проект '{dialog.result['name']}' создан с ID: {project_id}")
                    
                    if self.app_logger:
                        self.app_logger.log_ui_action("create_project", f"Проект {dialog.result['name']}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось создать проект")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать проект: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка создания проекта: {e}")
    
    def open_project(self):
        """Открыть проект автоматически"""
        try:
            if not self.db_manager:
                messagebox.showerror("Ошибка", "База данных не инициализирована")
                return
            
            # Выбор папки проекта
            folder_path = filedialog.askdirectory(title="Выберите папку проекта")
            if not folder_path:
                return
            
            project_path = Path(folder_path)
            
            # Проверяем, что это действительно папка проекта
            if not self._is_valid_project_folder(project_path):
                messagebox.showwarning("Внимание", "Выбранная папка не похожа на проект. Вы уверены, что хотите продолжить?")
            
            # Автоматическое создание/получение проекта
            self.current_project_id = self.db_manager.get_or_create_project(str(project_path))
            
            # Автоанализ проекта
            from shared.project_auto_analyzer import ProjectAutoAnalyzer
            analyzer = ProjectAutoAnalyzer(self.db_manager)
            
            # Запускаем автоанализ в отдельном потоке
            threading.Thread(
                target=self._auto_analyze_project, 
                args=(analyzer, str(project_path)), 
                daemon=True
            ).start()
            
            # Инициализация Git менеджера
            self.git_manager = GitManager(str(project_path), self.db_manager)
            
            # Обновляем Git контекст в фоне
            if self.git_manager.is_git_repo:
                threading.Thread(
                    target=self.git_manager.update_git_context, 
                    args=(self.current_project_id,), 
                    daemon=True
                ).start()
            
            # Сохраняем старую систему для совместимости
            self.project_context = ProjectContext(str(project_path))
            self.shared_chat_manager = SharedChatManager(str(project_path))
            self.project_context.update_context("project_opened", f"Проект открыт: {project_path}")
            
            # Обновляем UI
            self.refresh_project_details()
            self.status_bar.config(text=f"Проект: {project_path.name} (анализ...)")
            
            # Отправляем контекст в нейросеть
            if self.ollama_manager:
                threading.Thread(target=self.send_context_to_neuro, daemon=True).start()
            
            if self.app_logger:
                self.app_logger.log_project_open(str(project_path), self.current_project_id)
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть проект: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка открытия проекта: {e}")
    
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
    
    def _auto_analyze_project(self, analyzer: 'ProjectAutoAnalyzer', project_path: str):
        """Автоанализ проекта в фоновом потоке"""
        try:
            # Выполняем анализ
            project_data = analyzer.analyze_project(project_path)
            
            if project_data:
                # Обновляем статус в главном потоке
                self.root.after(0, lambda: self._update_project_status(project_data['name']))
                
                # Обновляем детали проекта
                self.root.after(0, lambda: self._update_project_details(project_data))
                
                self.logger.info(f"Проанализирован проект: {project_data['name']}")
            else:
                self.root.after(0, lambda: self.status_bar.config(text=f"Проект: {Path(project_path).name}"))
                
        except Exception as e:
            self.logger.error(f"Ошибка автоанализа проекта: {e}")
            self.root.after(0, lambda: self.status_bar.config(text=f"Проект: {Path(project_path).name} (ошибка анализа)"))
    
    def _update_project_status(self, project_name: str):
        """Обновление статуса проекта"""
        self.status_bar.config(text=f"Проект: {project_name}")
    
    def _update_project_details(self, project_data: Dict):
        """Обновление деталей проекта после анализа"""
        try:
            # Обновляем информацию о проекте в UI
            if hasattr(self, 'project_details_frame'):
                # Очищаем старую информацию
                for widget in self.project_details_frame.winfo_children():
                    widget.destroy()
                
                # Добавляем новую информацию
                self._display_project_info(project_data)
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления деталей проекта: {e}")
    
    def _display_project_info(self, project_data: Dict):
        """Отображение информации о проекте"""
        try:
            info_frame = ttk.LabelFrame(self.project_details_frame, text="Информация о проекте", padding=10)
            info_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Основная информация
            info_text = f"Название: {project_data.get('name', 'Неизвестно')}\n"
            info_text += f"Тип: {project_data.get('type', 'Неизвестно')}\n"
            info_text += f"Путь: {project_data.get('path', '')}\n"
            
            if project_data.get('description'):
                info_text += f"Описание: {project_data['description']}\n"
            
            # Технологии
            tech_stack = project_data.get('tech_stack', {})
            if tech_stack.get('languages'):
                languages = [lang['name'] for lang in tech_stack['languages'][:3]]
                info_text += f"Языки: {', '.join(languages)}\n"
            
            if tech_stack.get('frameworks'):
                frameworks = [fw['name'] for fw in tech_stack['frameworks'][:2]]
                info_text += f"Фреймворки: {', '.join(frameworks)}\n"
            
            # Git информация
            git_info = project_data.get('git_info', {})
            if git_info.get('is_git_repo'):
                info_text += f"Git: {git_info.get('current_branch', 'main')}\n"
            
            ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
            
        except Exception as e:
            self.logger.error(f"Ошибка отображения информации о проекте: {e}")
    
    def add_project(self):
        """Добавление проекта вручную (устаревший метод)"""
        folder_path = filedialog.askdirectory(title="Выберите папку проекта")
        if folder_path:
            project_path = Path(folder_path)
            if (project_path / ".project_context.json").exists():
                self.projects.append({
                    'name': project_path.name,
                    'path': str(project_path),
                    'type': 'manual'
                })
                
                self.project_listbox.insert(tk.END, f"{project_path.name} (manual)")
                self.status_bar.config(text=f"Проект добавлен: {project_path.name}")
            else:
                messagebox.showwarning("Внимание", "В папке не найден контекст проекта")
    
    def remove_project(self):
        """Удаление проекта из списка"""
        selection = self.project_listbox.curselection()
        if selection:
            project_name = self.project_listbox.get(selection[0]).split(" (")[0]
            self.projects = [p for p in self.projects if p['name'] != project_name]
            self.project_listbox.delete(selection[0])
            self.status_bar.config(text=f"Проект удален: {project_name}")
    
    def on_project_select(self, event):
        """Обработка выбора проекта"""
        selection = self.project_listbox.curselection()
        if selection:
            project_name = self.project_listbox.get(selection[0]).split(" (")[0]
            project = next(p for p in self.projects if p['name'] == project_name)
            
            self.current_project_path = project['path']
            self.project_name_label.config(text=f"Проект: {project_name}")
            self.project_path_label.config(text=f"Путь: {project['path']}")
            
            # Загружаем детали проекта
            self.load_project_details(project['path'])
            project_context = ProjectContext(project['path'])
            context_data = project_context.load_context()
            
            # Инициализация общего чата
            self.shared_chat_manager = SharedChatManager(project['path'])
    
    def load_project_details(self, project_path):
        """Загрузка деталей проекта"""
        try:
            self.current_project_path = project_path
            project_context = ProjectContext(project_path)
            context_data = project_context.load_context()
            
            # Инициализация общего чата
            self.shared_chat_manager = SharedChatManager(project_path)
            self.last_chat_timestamp = None
            
            # Обновляем информацию о проекте
            project_name = Path(project_path).name
            self.project_name_label.config(text=f"Проект: {project_name}")
            self.project_path_label.config(text=f"Путь: {project_path}")
            
            # Подсчет файлов и папок
            file_count = len(context_data.get('file_structure', {}).get('files', []))
            folder_count = len(context_data.get('file_structure', {}).get('folders', []))
            
            self.project_files_label.config(text=f"Файлов: {file_count}")
            self.project_folders_label.config(text=f"Папок: {folder_count}")
            
            # Обновляем историю
            self.update_history_display(context_data.get('context_history', []))
            
            # Обновляем структуру
            self.update_structure_display(context_data.get('file_structure', {}))
            
            self.status_bar.config(text=f"Загружен проект: {project_name}")
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки деталей проекта: {e}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить детали проекта: {e}")
    
    def update_history_display(self, history):
        """Обновление отображения истории"""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete(1.0, tk.END)
        
        for entry in reversed(history[-10:]):  # Последние 10 записей
            timestamp = entry.get('timestamp', '')
            action = entry.get('action', '')
            details = entry.get('details', '')
            
            self.history_text.insert(tk.END, f"📅 {timestamp}\n")
            self.history_text.insert(tk.END, f"🔧 {action}\n")
            self.history_text.insert(tk.END, f"📝 {details}\n")
            self.history_text.insert(tk.END, "-" * 50 + "\n\n")
        
        self.history_text.config(state=tk.DISABLED)
    
    def update_structure_display(self, structure):
        """Обновление отображения структуры"""
        # Очищаем дерево
        for item in self.structure_tree.get_children():
            self.structure_tree.delete(item)
        
        # Добавляем структуру
        self.add_structure_to_tree(structure, "")
    
    def add_structure_to_tree(self, structure, parent_node):
        """Рекурсивное добавление структуры в дерево"""
        if 'folders' in structure:
            for folder in structure['folders']:
                node = self.structure_tree.insert(parent_node, "end", text=f"📁 {folder['name']}", values=("", "folder"))
                self.add_structure_to_tree(folder, node)
        
        if 'files' in structure:
            for file in structure['files']:
                size = f"{file['size']} байт" if file['size'] < 1024 else f"{file['size']//1024} КБ"
                self.structure_tree.insert(parent_node, "end", text=f"📄 {file['name']}", values=(size, "file"))
    
    def clear_project_details(self):
        """Очистка деталей проекта"""
        self.project_name_label.config(text="Проект не выбран")
        self.project_path_label.config(text="Путь: -")
        self.project_files_label.config(text="Файлов: -")
        self.project_folders_label.config(text="Папок: -")
        
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete(1.0, tk.END)
        self.history_text.config(state=tk.DISABLED)
        
        for item in self.structure_tree.get_children():
            self.structure_tree.delete(item)
    
    def on_flow_mode_changed(self):
        """Обработка изменения режима поточности данных"""
        mode = self.flow_mode.get()
        mode_text = {
            "ide": "Текущий режим: Только IDE",
            "office": "Текущий режим: Только Office", 
            "both": "Текущий режим: IDE + Office"
        }
        self.flow_status_label.config(text=mode_text.get(mode, "Неизвестный режим"))
        self.status_bar.config(text=f"Режим поточности изменен: {mode_text.get(mode, '')}")
    
    def select_txt_file(self):
        """Выбор .txt файла для работы"""
        if not hasattr(self, 'current_project_path') or not self.current_project_path:
            messagebox.showwarning("Внимание", "Сначала выберите проект")
            return
        
        file_path = filedialog.askopenfilename(
            title="Выберите .txt файл",
            initialdir=self.current_project_path,
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        
        if file_path:
            self.load_txt_file(file_path)
    
    def load_txt_file(self, file_path):
        """Загрузка .txt файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.current_txt_file = Path(file_path)
            self.txt_file_content = content
            self.original_txt_content = content
            self.txt_file_modified = False
            
            # Обновляем интерфейс
            self.txt_file_label.config(text=f"📄 {self.current_txt_file.name}", foreground="black")
            
            # Отображаем содержимое
            self.txt_content.delete(1.0, tk.END)
            
            # Ограничиваем отображение до 10000 символов для больших файлов
            display_content = content[:10000]
            if len(content) > 10000:
                display_content += "\n\n... (файл обрезан, первые 10000 символов)"
            
            self.txt_content.insert(1.0, display_content)
            
            self.status_bar.config(text=f"Загружен файл: {self.current_txt_file.name} ({len(content)} символов)")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")
            self.logger.error(f"Ошибка загрузки файла: {e}")
    
    def on_txt_content_changed(self, event=None):
        """Обработка изменений в тексте .txt файла"""
        if self.current_txt_file and not self.txt_file_modified:
            current_content = self.txt_content.get(1.0, tk.END).strip()
            if current_content != self.original_txt_content.strip():
                self.txt_file_modified = True
                self.txt_file_label.config(text=f"📄 {self.current_txt_file.name} *", foreground="red")
                self.status_bar.config(text=f"Файл изменен: {self.current_txt_file.name}")
    
    def save_txt_file(self):
        """Сохранение изменений в .txt файле"""
        if not self.current_txt_file:
            messagebox.showwarning("Внимание", "Файл не выбран")
            return
        
        try:
            content = self.txt_content.get(1.0, tk.END).rstrip()
            with open(self.current_txt_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Обновляем состояние
            self.txt_file_content = content
            self.original_txt_content = content
            self.txt_file_modified = False
            
            # Обновляем интерфейс
            self.txt_file_label.config(text=f"📄 {self.current_txt_file.name}", foreground="black")
            self.status_bar.config(text=f"Файл сохранен: {self.current_txt_file.name}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
    
    def clear_txt_content(self):
        """Очистка содержимого .txt файла"""
        self.txt_content.delete(1.0, tk.END)
        self.txt_file_label.config(text="Файл не выбран", foreground="gray")
        self.current_txt_file = None
        self.txt_file_content = ""
        self.original_txt_content = ""
        self.txt_file_modified = False
        self.status_bar.config(text="Поле очищено")
    
    def refresh_txt_file(self):
        """Обновление содержимого .txt файла"""
        if self.current_txt_file:
            self.load_txt_file(str(self.current_txt_file))
    
    def ask_ai_about_file(self):
        """Задать вопрос AI о .txt файле или проекте"""
        if not self.ollama_manager:
            messagebox.showwarning("Внимание", "AI не доступен")
            return
        
        question = self.ai_question.get(1.0, tk.END).strip()
        if not question:
            messagebox.showwarning("Внимание", "Введите вопрос")
            return
        
        # Получаем текущий режим поточности
        flow_mode = self.flow_mode.get()
        
        # Проверяем режим работы
        if flow_mode == "ide":
            # Режим только IDE - показываем информацию, что запрос уйдет в IDE
            self.ai_response.config(state=tk.NORMAL)
            self.ai_response.delete(1.0, tk.END)
            self.ai_response.insert(1.0, f"[РЕЖИМ: Только IDE]\n\nВопрос: {question}\n\nОтвет будет получен в StartIDE.\n\nПожалуйста, переключитесь в StartIDE для просмотра ответа.")
            self.ai_response.config(state=tk.DISABLED)
            self.status_bar.config(text="Запрос отправлен в StartIDE")
            return
        
        # Для режимов "office" и "both" - обрабатываем в Office
        
        # Если файл не выбран, используем контекст проекта
        if not self.current_txt_file or not self.txt_file_content:
            if hasattr(self, 'current_project_path') and self.current_project_path:
                # Используем контекст проекта
                response = self.ollama_manager.ask_about_project(question, self.current_project_path)
                
                mode_prefix = "[РЕЖИМ: IDE + Office]\n\n" if flow_mode == "both" else "[РЕЖИМ: Только Office]\n\n"
                
                self.ai_response.config(state=tk.NORMAL)
                self.ai_response.delete(1.0, tk.END)
                self.ai_response.insert(1.0, f"{mode_prefix}Вопрос о проекте:\n{question}\n\nОтвет:\n{response}")
                self.ai_response.config(state=tk.DISABLED)
                
                if flow_mode == "both":
                    self.status_bar.config(text="Ответ получен в Office и доступен в IDE")
                else:
                    self.status_bar.config(text="Ответ получен в Office")
            else:
                messagebox.showwarning("Внимание", "Выберите проект или .txt файл")
            return
        
        # Если файл выбран - задаем вопрос о файле
        def get_response():
            # Формируем контекст с содержимым файла
            context = f"Содержимое файла {self.current_txt_file.name}:\n\n{self.txt_file_content}\n\nВопрос: {question}"
            
            response = self.ollama_manager.session.post(f"{self.ollama_manager.base_url}/api/generate",
                json={
                    "model": self.ollama_manager.model,
                    "prompt": context,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get('response', 'Нет ответа')
            else:
                ai_response = f"Ошибка: {response.status_code}"
            
            mode_prefix = "[РЕЖИМ: IDE + Office]\n\n" if flow_mode == "both" else "[РЕЖИМ: Только Office]\n\n"
            
            self.ai_response.config(state=tk.NORMAL)
            self.ai_response.delete(1.0, tk.END)
            self.ai_response.insert(1.0, f"{mode_prefix}Вопрос о файле {self.current_txt_file.name}:\n{question}\n\nОтвет:\n{ai_response}")
            self.ai_response.config(state=tk.DISABLED)
            
            if flow_mode == "both":
                self.status_bar.config(text=f"Ответ о файле {self.current_txt_file.name} получен в Office и доступен в IDE")
            else:
                self.status_bar.config(text=f"Ответ о файле {self.current_txt_file.name} получен в Office")
        
        threading.Thread(target=get_response, daemon=True).start()
    
    def update_project_context(self):
        """Обновление контекста проекта"""
        if not self.ollama_manager or not hasattr(self, 'current_project_path'):
            messagebox.showwarning("Внимание", "AI не доступен или проект не выбран")
            return
        
        def update_context():
            try:
                project_context = ProjectContext(self.current_project_path)
                context_data = project_context.load_context()
                success = self.ollama_manager.send_project_context(self.current_project_path, context_data)
                
                if success:
                    self.status_bar.config(text="Контекст проекта обновлен")
                else:
                    self.status_bar.config(text="Ошибка обновления контекста")
            except Exception as e:
                self.logger.error(f"Ошибка обновления контекста: {e}")
                self.status_bar.config(text="Ошибка обновления контекста")
        
        threading.Thread(target=update_context, daemon=True).start()
    
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
                    
                    if msg.get("timestamp", "") > (self.last_chat_timestamp or ""):
                        self.last_chat_timestamp = msg.get("timestamp")
                
                self.chat_history.see(tk.END)
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
            messagebox.showwarning("Внимание", "Сначала выберите проект")
            return
        
        message = self.chat_message.get(1.0, tk.END).strip()
        if not message:
            return
        
        success = self.shared_chat_manager.add_message(
            sender="StartOffice",
            message_type="text",
            content=message
        )
        
        if success:
            self.chat_message.delete(1.0, tk.END)
            self.refresh_chat()
            self.status_bar.config(text="Сообщение отправлено в чат")
        else:
            messagebox.showerror("Ошибка", "Не удалось отправить сообщение")
    
    def send_file_to_chat(self):
        """Отправка файла в чат для анализа"""
        if not self.shared_chat_manager:
            messagebox.showwarning("Внимание", "Сначала выберите проект")
            return
        
        if not hasattr(self, 'current_project_path') or not self.current_project_path:
            messagebox.showwarning("Внимание", "Сначала выберите проект")
            return
        
        file_path = filedialog.askopenfilename(
            title="Выберите файл для отправки в чат",
            initialdir=self.current_project_path,
            filetypes=[("Python файлы", "*.py"), ("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            question = messagebox.askquestion(
                "Отправка файла",
                "Добавить вопрос/комментарий к файлу?",
                icon='question'
            )
            
            comment = ""
            if question == 'yes':
                comment = tk.simpledialog.askstring(
                    "Комментарий",
                    "Введите вопрос или комментарий:",
                    initialvalue="Проанализируй этот файл"
                ) or "Проанализируй этот файл"
            
            success = self.shared_chat_manager.send_file_for_analysis(
                sender="StartOffice",
                file_path=file_path,
                question=comment
            )
            
            if success:
                self.refresh_chat()
                self.status_bar.config(text=f"Файл {Path(file_path).name} отправлен в чат")
                # Переключаемся на вкладку чата
                self.notebook.select(self.chat_frame)
            else:
                messagebox.showerror("Ошибка", "Не удалось отправить файл")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить файл: {e}")
    
    def schedule_chat_refresh(self):
        """Планирование автоматического обновления чата"""
        if hasattr(self, 'current_project_path') and self.current_project_path:
            self.refresh_chat()
        
        self.root.after(5000, self.schedule_chat_refresh)
    
    def setup_document_tab(self):
        """Настройка вкладки документа"""
        # Панель инструментов документа
        doc_toolbar = ttk.Frame(self.document_frame)
        doc_toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        # Выбор файла документа
        ttk.Label(doc_toolbar, text="Файл документа:").pack(side=tk.LEFT, padx=5)
        self.document_path_var = tk.StringVar(value="Выберите файл...")
        self.document_path_entry = ttk.Entry(doc_toolbar, textvariable=self.document_path_var, width=40)
        self.document_path_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(doc_toolbar, text="📁 Обзор", command=self.browse_document_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(doc_toolbar, text="💾 Сохранить", command=self.save_document).pack(side=tk.LEFT, padx=2)
        
        # Разделитель
        ttk.Separator(doc_toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Голосовой ввод для документа (улучшенная версия)
        if ADVANCED_VOICE_INPUT_AVAILABLE:
            self.voice_doc_button = ttk.Button(doc_toolbar, text="🎤 Голос (реальное время)", command=self.toggle_advanced_document_voice_input)
            self.voice_doc_button.pack(side=tk.LEFT, padx=2)
            self.is_recording_document_voice = False
            self.voice_doc_status = ttk.Label(doc_toolbar, text="", foreground="blue")
            self.voice_doc_status.pack(side=tk.LEFT, padx=5)
        elif VOICE_INPUT_AVAILABLE:
            self.voice_doc_button = ttk.Button(doc_toolbar, text="🎤 Голосовой ввод", command=self.toggle_document_voice_input)
            self.voice_doc_button.pack(side=tk.LEFT, padx=2)
            self.is_recording_document_voice = False
        else:
            ttk.Button(doc_toolbar, text="🎤 Голос (недоступен)", state=tk.DISABLED).pack(side=tk.LEFT, padx=2)
        
        # Редактор документа
        editor_frame = ttk.LabelFrame(self.document_frame, text="Редактор документа")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Текстовый редактор с прокруткой
        text_container = ttk.Frame(editor_frame)
        text_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.document_editor = tk.Text(text_container, wrap=tk.WORD, font=("Consolas", 11))
        doc_scrollbar_y = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.document_editor.yview)
        doc_scrollbar_x = ttk.Scrollbar(text_container, orient=tk.HORIZONTAL, command=self.document_editor.xview)
        
        self.document_editor.grid(row=0, column=0, sticky="nsew")
        doc_scrollbar_y.grid(row=0, column=1, sticky="ns")
        doc_scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        text_container.grid_rowconfigure(0, weight=1)
        text_container.grid_columnconfigure(0, weight=1)
        
        self.document_editor.config(yscrollcommand=doc_scrollbar_y.set, xscrollcommand=doc_scrollbar_x.set)
        
        # AI помощник для документа
        ai_assistant_frame = ttk.LabelFrame(self.document_frame, text="AI Помощник")
        ai_assistant_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Кнопки AI помощника
        ai_buttons_frame = ttk.Frame(ai_assistant_frame)
        ai_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(ai_buttons_frame, text="📄 Загрузить context.txt", command=self.load_context_to_ai).pack(side=tk.LEFT, padx=2)
        ttk.Button(ai_buttons_frame, text="🤖 Создать отчёт", command=self.generate_report_with_ai).pack(side=tk.LEFT, padx=2)
        
        # Статус AI
        self.ai_doc_status = ttk.Label(ai_assistant_frame, text="Готов к работе", foreground="green")
        self.ai_doc_status.pack(pady=2)
        
        # Переменные для документа
        self.current_document_path = None
        self.document_modified = False
        
        # Отслеживание изменений в документе
        self.document_editor.bind('<KeyRelease>', self.on_document_changed)
        self.document_editor.bind('<Button-1>', self.on_document_changed)
    
    def browse_document_file(self):
        """Выбор файла документа"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл документа",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if file_path:
            self.load_document(file_path)
    
    def load_document(self, file_path):
        """Загрузка документа"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.document_editor.delete(1.0, tk.END)
            self.document_editor.insert(1.0, content)
            
            self.current_document_path = Path(file_path)
            self.document_path_var.set(str(self.current_document_path))
            self.document_modified = False
            
            if self.app_logger:
                self.app_logger.log_file_action("open", str(file_path))
            
            self.status_bar.config(text=f"Документ загружен: {self.current_document_path.name}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить документ: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка загрузки документа: {e}")
    
    def save_document(self):
        """Сохранение документа"""
        if not self.current_document_path:
            # Сохраняем как новый файл
            file_path = filedialog.asksaveasfilename(
                title="Сохранить документ как",
                defaultextension=".txt",
                filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
            )
            if not file_path:
                return
            self.current_document_path = Path(file_path)
            self.document_path_var.set(str(self.current_document_path))
        
        try:
            content = self.document_editor.get(1.0, tk.END).rstrip()
            with open(self.current_document_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.document_modified = False
            
            if self.app_logger:
                self.app_logger.log_file_action("save", str(self.current_document_path))
            
            self.status_bar.config(text=f"Документ сохранен: {self.current_document_path.name}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить документ: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка сохранения документа: {e}")
    
    def on_document_changed(self, event=None):
        """Отслеживание изменений в документе"""
        if not self.document_modified:
            self.document_modified = True
            if self.current_document_path:
                self.status_bar.config(text=f"Документ изменен: {self.current_document_path.name}*")
    
    def toggle_advanced_document_voice_input(self):
        """Переключение улучшенного голосового ввода для документа с реальным временем"""
        if not ADVANCED_VOICE_INPUT_AVAILABLE or not self.advanced_voice_input_manager:
            messagebox.showwarning("Голосовой ввод", "Улучшенный голосовой ввод недоступен. Установите speechrecognition.")
            return
        
        if not self.is_recording_document_voice:
            # Начинаем непрерывную запись для документа
            self.voice_doc_button.config(text="⏹️ Остановить запись")
            self.is_recording_document_voice = True
            
            # Настраиваем для документов
            self.advanced_voice_input_manager.set_language("ru-RU")
            self.advanced_voice_input_manager.set_sensitivity(0.8)  # Более чувствительный для документов
            
            # Устанавливаем callback для частичного распознавания
            def partial_callback(text):
                # Показываем распознаваемое слово в статусе
                if hasattr(self, 'voice_doc_status'):
                    self.voice_doc_status.config(text=f"🗣️: {text}")
            
            # Устанавливаем callback для финального текста
            def final_callback(text):
                if text.strip():
                    if hasattr(self, 'voice_doc_status'):
                        self.voice_doc_status.config(text=f"✅: {text[:20]}...")
            
            self.advanced_voice_input_manager.set_partial_text_callback(partial_callback)
            self.advanced_voice_input_manager.set_text_callback(final_callback)
            
            # Начинаем непрерывную запись
            self.advanced_voice_input_manager.start_continuous_document_recording(self.document_editor)
            
            if self.app_logger:
                self.app_logger.log_voice_action("start", "Начат улучшенный голосовой ввод для документа (реальное время)")
            
            self.status_bar.config(text="🎤 Голосовой ввод в документ (реальное время)...")
        else:
            # Останавливаем запись
            self.voice_doc_button.config(text="🎤 Голос (реальное время)")
            self.is_recording_document_voice = False
            
            final_text = self.advanced_voice_input_manager.stop_document_recording()
            
            # Обновляем статус
            if hasattr(self, 'voice_doc_status'):
                self.voice_doc_status.config(text="✅ Готово")
            
            if self.app_logger:
                self.app_logger.log_voice_action("stop", f"Завершен улучшенный голосовой ввод для документа: {final_text[:50]}...")
            
            self.status_bar.config(text="Готов к работе")
    
    def toggle_document_voice_input(self):
        """Переключение базового голосового ввода для документа"""
        if not VOICE_INPUT_AVAILABLE or not self.voice_input_manager:
            messagebox.showwarning("Голосовой ввод", "Голосовой ввод недоступен. Установите speechrecognition.")
            return
        
        if not self.is_recording_document_voice:
            # Начинаем запись
            self.voice_doc_button.config(text="⏹️ Остановить запись")
            self.is_recording_document_voice = True
            
            # Устанавливаем callback для вставки текста
            self.voice_input_manager.set_text_callback(None)  # Сбрасываем старый callback
            self.voice_input_manager.start_document_recording(self.document_editor)
            
            if self.app_logger:
                self.app_logger.log_voice_action("start", "Начат голосовой ввод для документа")
            
            self.status_bar.config(text="🎤 Голосовая запись в документ...")
        else:
            # Останавливаем запись
            self.voice_doc_button.config(text="🎤 Голосовой ввод")
            self.is_recording_document_voice = False
            
            recognized_text = self.voice_input_manager.stop_document_recording()
            
            if self.app_logger:
                self.app_logger.log_voice_action("stop", f"Распознано для документа: {recognized_text[:50]}...")
            
            self.status_bar.config(text="Готов к работе")
    
    def load_context_to_ai(self):
        """Загрузка context.txt в нейросеть для анализа"""
        try:
            # Ищем context.txt в папке проекта
            context_file = None
            if self.current_project_id and self.db_manager:
                project_info = self.db_manager.get_project_by_id(self.current_project_id)
                if project_info:
                    project_path = Path(project_info['path'])
                    context_file = project_path / "context.txt"
            
            if not context_file or not context_file.exists():
                messagebox.showwarning("Внимание", "Файл context.txt не найден в проекте")
                return
            
            with open(context_file, 'r', encoding='utf-8') as f:
                context_content = f.read()
            
            if not self.ollama_manager:
                messagebox.showwarning("AI недоступен", "Подключение к AI не установлено")
                return
            
            # Отправляем контекст в нейросеть для анализа
            self.ai_doc_status.config(text="Отправляю контекст в AI...", foreground="orange")
            
            def send_context():
                try:
                    # Отправляем запрос в AI для анализа контекста
                    prompt = f"Проанализируй следующий контекст проекта и предоставь краткую информацию:\n\n{context_content}"
                    
                    response = self.ollama_manager.ask_question(prompt)
                    
                    # Показываем результат в отдельном окне
                    self.root.after(0, lambda: self.show_ai_response("Анализ контекста", response))
                    
                    # Обновляем статус
                    self.root.after(0, lambda: self.ai_doc_status.config(text="Контекст проанализирован", foreground="green"))
                    self.root.after(0, lambda: self.status_bar.config(text="Контекст отправлен в AI"))
                    
                    if self.app_logger:
                        self.app_logger.log_ai_interaction("Анализ контекста", True)
                    
                except Exception as e:
                    self.root.after(0, lambda: self.ai_doc_status.config(text="Ошибка анализа", foreground="red"))
                    self.root.after(0, lambda: self.status_bar.config(text="Ошибка анализа контекста"))
                    
                    if self.app_logger:
                        self.app_logger.log_ai_interaction("Анализ контекста", False)
                    if self.app_logger:
                        self.app_logger.log_error(f"Ошибка анализа контекста: {e}")
            
            # Запускаем в отдельном потоке
            threading.Thread(target=send_context, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить context.txt: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка загрузки context.txt: {e}")
    
    def show_ai_response(self, title: str, response: str):
        """Показать ответ AI в отдельном окне"""
        response_window = tk.Toplevel(self.root)
        response_window.title(title)
        response_window.geometry("600x400")
        response_window.transient(self.root)
        
        from tkinter import scrolledtext
        text_widget = scrolledtext.ScrolledText(response_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(1.0, response)
        text_widget.config(state=tk.DISABLED)
        
        # Кнопка закрытия
        ttk.Button(response_window, text="Закрыть", command=response_window.destroy).pack(pady=5)
        if not document_content:
            messagebox.showwarning("Пустой документ", "Сначала загрузите context.txt или напишите текст")
            return
        
        try:
            self.ai_doc_status.config(text="Создаю отчёт...", foreground="orange")
            
            # Отправляем запрос в AI
            prompt = "Напиши отчёт как офисный сотрудник по проекту на основе следующей информации:\n\n" + document_content
            
            def generate_report():
                try:
                    response = self.ollama_manager.ask_question(prompt)
                    
                    # Вставляем ответ в документ
                    self.document_editor.delete(1.0, tk.END)
                    self.document_editor.insert(1.0, f"ОТЧЁТ ПО ПРОЕКТУ\n\n{response}")
                    
                    # Обновляем статус
                    self.root.after(0, lambda: self.ai_doc_status.config(text="Отчёт создан", foreground="green"))
                    self.root.after(0, lambda: self.status_bar.config(text="Отчёт успешно создан"))
                    
                    if self.app_logger:
                        self.app_logger.log_ai_interaction("Создание отчёта", True)
                    
                except Exception as e:
                    self.root.after(0, lambda: self.ai_doc_status.config(text="Ошибка создания", foreground="red"))
                    self.root.after(0, lambda: self.status_bar.config(text="Ошибка создания отчёта"))
                    
                    if self.app_logger:
                        self.app_logger.log_ai_interaction("Создание отчёта", False)
                    if self.app_logger:
                        self.app_logger.log_error(f"Ошибка создания отчёта: {e}")
            
            # Запускаем в отдельном потоке
            threading.Thread(target=generate_report, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать отчёт: {e}")
            self.ai_doc_status.config(text="Ошибка", foreground="red")
    
    def open_project_manager(self):
        """Открыть окно управления проектами"""
        try:
            if not self.db_manager:
                messagebox.showerror("Ошибка", "База данных не инициализирована")
                return
            
            # Импортируем окно управления проектами из StartIDE
            from StartIDE.project_manager_window import ProjectManagerWindow
            ProjectManagerWindow(self.root, self.db_manager, self.app_logger)
            
            if self.app_logger:
                self.app_logger.log_ui_action("open_project_manager", "Открыто окно управления проектами")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть управление проектами: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка открытия управления проектами: {e}")
    
    def open_file_manager(self):
        """Открыть управление файлами текущего проекта"""
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
    
    def quit_app(self):
        """Выход из приложения"""
        # Закрытие ресурсов
        if self.db_manager:
            self.db_manager.close()
        if self.voice_input_manager:
            self.voice_input_manager.cleanup()
        if self.advanced_voice_input_manager:
            self.advanced_voice_input_manager.cleanup()
        
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
            if hasattr(widget, 'get') and widget == getattr(self, 'document_editor', None):
                # Если в фокусе редактор документов, используем голосовой ввод для документов
                if ADVANCED_VOICE_INPUT_AVAILABLE and self.advanced_voice_input_manager:
                    self.toggle_advanced_document_voice_input()
                elif VOICE_INPUT_AVAILABLE and self.voice_input_manager:
                    self.toggle_document_voice_input()
            elif hasattr(widget, 'get') and widget == getattr(self, 'txt_content', None):
                # Если в фокусе содержимое txt файла
                if hasattr(self, 'ask_ai_about_file'):
                    self.ask_ai_about_file()
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
    
    def save_current_file(self):
        """Сохранить текущий файл"""
        try:
            # Проверяем, какой виджет в фокусе
            widget = self.root.focus_get()
            if hasattr(widget, 'get') and widget == getattr(self, 'document_editor', None):
                # Сохраняем документ
                if hasattr(self, 'current_document_path') and self.current_document_path:
                    self.save_document()
            elif hasattr(widget, 'get') and widget == getattr(self, 'txt_content', None):
                # Сохраняем txt файл
                if hasattr(self, 'current_txt_file') and self.current_txt_file:
                    self.save_txt_file()
        except:
            pass
    
    def generate_report_with_ai(self):
        """Создание отчёта с помощью AI"""
        try:
            if not self.ollama_manager or not self.ollama_manager.test_connection():
                messagebox.showerror("Ошибка", "AI недоступен. Проверьте подключение к Ollama.")
                return
            
            # Получаем контекст из документа
            document_content = self.document_editor.get("1.0", tk.END).strip()
            if not document_content:
                messagebox.showwarning("Внимание", "Документ пустой. Добавьте содержимое для анализа.")
                return
            
            # Формируем запрос к AI
            prompt = f"""Проанализируй следующий текст и создай структурированный отчёт:

{document_content}

Отчёт должен включать:
1. Краткое содержание
2. Основные моменты
3. Рекомендации
4. Заключение

Ответ на русском языке."""
            
            # Отправляем запрос
            response = self.ollama_manager.session.post(
                f"{self.ollama_manager.base_url}/api/generate",
                json={
                    "model": self.ollama_manager.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get('response', 'Нет ответа')
                
                # Создаем новое окно с отчётом
                report_window = tk.Toplevel(self.root)
                report_window.title("AI Отчёт")
                report_window.geometry("800x600")
                
                # Текстовое поле для отчёта
                report_text = scrolledtext.ScrolledText(report_window, wrap=tk.WORD, font=("Arial", 10))
                report_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                report_text.insert("1.0", ai_response)
                report_text.config(state=tk.DISABLED)
                
                # Кнопка закрытия
                ttk.Button(report_window, text="Закрыть", command=report_window.destroy).pack(pady=5)
                
                # Обновляем статус
                self.ai_doc_status.config(text="Отчёт создан", foreground="green")
                
            else:
                messagebox.showerror("Ошибка", f"Не удалось получить ответ от AI: {response.status_code}")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка создания отчёта: {e}")
    
    def check_connection(self):
        """Проверка подключения к AI в отдельном потоке"""
        try:
            if self.ollama_manager and self.ollama_manager.test_connection():
                if hasattr(self, 'ai_status_label'):
                    self.ai_status_label.config(text="Статус: Подключено", foreground="green")
            else:
                if hasattr(self, 'ai_status_label'):
                    self.ai_status_label.config(text="Статус: Не подключено", foreground="red")
        except Exception as e:
            if hasattr(self, 'ai_status_label'):
                self.ai_status_label.config(text="Статус: Ошибка", foreground="red")
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

if __name__ == "__main__":
    app = StartOffice()
    app.run()
