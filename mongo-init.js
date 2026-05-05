// Инициализация базы данных START-beta
db = db.getSiblingDB('start_beta');

// Создание коллекций
db.createCollection('projects');
db.createCollection('file_contents');
db.createCollection('ai_contexts');
db.createCollection('full_conversations');
db.createCollection('ai_responses_cache');

// Создание индексов для быстрого поиска
db.projects.createIndex({ "name": 1 }, { unique: true });
db.projects.createIndex({ "path": 1 }, { unique: true });
db.file_contents.createIndex({ "project_id": 1, "file_path": 1 });
db.ai_contexts.createIndex({ "project_id": 1 }, { unique: true });
db.full_conversations.createIndex({ "project_id": 1, "session_id": 1 });
db.ai_responses_cache.createIndex({ "prompt_hash": 1 }, { unique: true });
db.ai_responses_cache.createIndex({ "created_at": 1 }, { expireAfterSeconds: 86400 }); // TTL 24 часа

// Создание пользователя приложения
db.createUser({
  user: 'start_app',
  pwd: 'app_password',
  roles: [
    { role: 'readWrite', db: 'start_beta' }
  ]
});

print('Database start_beta initialized successfully');
