import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import os
from pathlib import Path
import threading
import logging

# Добавляем путь к shared модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.ollama_manager import OllamaManager
from shared.project_context import ProjectContext
from shared.shared_chat_manager import SharedChatManager

class StartOffice:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Start Office")
        self.root.geometry("1000x700")
        
        # Переменные
        self.ollama_manager = None
        self.projects = []
        
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Создание интерфейса
        self.setup_ui()
        
        # Попытка подключения к Ollama
        self.init_ollama()
        
        # Поиск проектов
        self.discover_projects()
    
    def setup_ui(self):
        """Создание интерфейса"""
        # Главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Файл меню
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Добавить проект", command=self.add_project)
        file_menu.add_command(label="Обновить проекты", command=self.discover_projects)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        
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
    
    def add_project(self):
        """Добавление проекта вручную"""
        folder_path = filedialog.askdirectory(title="Выберите папку проекта")
        if folder_path:
            project_path = Path(folder_path)
            if (project_path / ".project_context.json").exists():
                if str(project_path) not in self.projects:
                    self.projects.append(str(project_path))
                    self.project_listbox.insert(tk.END, project_path.name)
                    self.status_bar.config(text=f"Проект добавлен: {project_path.name}")
                else:
                    messagebox.showwarning("Внимание", "Этот проект уже добавлен")
            else:
                messagebox.showwarning("Внимание", "В папке не найден контекст проекта")
    
    def remove_project(self):
        """Удаление проекта из списка"""
        selection = self.project_listbox.curselection()
        if selection:
            index = selection[0]
            project_name = self.project_listbox.get(index)
            
            if messagebox.askyesno("Подтверждение", f"Удалить проект {project_name} из списка?"):
                del self.projects[index]
                self.project_listbox.delete(index)
                self.clear_project_details()
                self.status_bar.config(text=f"Проект удален: {project_name}")
    
    def on_project_select(self, event):
        """Обработка выбора проекта"""
        selection = self.project_listbox.curselection()
        if selection:
            index = selection[0]
            project_path = self.projects[index]
            self.load_project_details(project_path)
    
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
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

if __name__ == "__main__":
    app = StartOffice()
    app.run()
