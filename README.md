# 🧠 Emotion Analysis System

Платформа для анализа эмоционального состояния сотрудников на основе ежедневных текстовых отчётов. Использует RuBERT для классификации эмоций и расчёта индекса выгорания. *Учебный проект*

---

## ✨ Возможности

- **Анализ текста** — классификация эмоций (позитивное / нейтральное / негативное) через RuBERT с контекстной постобработкой
- **Индекс выгорания** — комплексный расчёт на основе эмоционального фона, семантических маркеров и истории отчётов
- **Три роли пользователей** — сотрудник, руководитель, HR-администратор с разными уровнями доступа
- **Аналитика команды** — динамика, распределение по уровням, ключевые слова из отчётов
- **Экспорт данных** — сводные и детальные CSV-отчёты для HR
- **Конфиденциальность** — тексты отчётов сотрудников не доступны руководителям

---

## 🛠 Стек технологий

| Компонент       | Технология                                                        |
|-----------------|-------------------------------------------------------------------|
| Backend         | FastAPI + Uvicorn                                                 |
| ML-модель       | [MonoHime/rubert-base-cased-sentiment-new](https://huggingface.co/MonoHime/rubert-base-cased-sentiment-new) |
| База данных     | PostgreSQL + psycopg2 (connection pool)                           |
| Шаблоны         | Jinja2                                                            |
| Frontend        | Vanilla JS + Chart.js + Flatpickr + Lucide Icons                  |
| Контейнеризация | Docker                                                            |

---

## 👥 Роли пользователей

| Роль               | Доступ                                                                 |
|--------------------|------------------------------------------------------------------------|
| **Сотрудник**      | Написание отчётов, личная аналитика, история, риск выгорания           |
| **Руководитель**   | Сводка по отделу, метаданные отчётов команды (без текстов), графики    |
| **HR-администратор** | Аналитика по всей компании, экспорт данных в CSV                    |

---

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- PostgreSQL 14+
- Docker (опционально)

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-username/emotion-analysis-system.git
cd emotion-analysis-system
```

### 2. Настройка окружения

```bash
cp .env.example .env
```

Заполните `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/emotion_db
```

### 3. Установка зависимостей

```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

pip install -r requirements.txt
```

> ⚠️ При первом запуске модель RuBERT (~700 МБ) загружается автоматически с Hugging Face.

### 4. Инициализация базы данных

```bash
# Создайте базу данных вручную:
psql -U postgres -c "CREATE DATABASE emotion_db;"

# Таблицы создаются автоматически при первом запуске приложения
```

### 5. Запуск

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Приложение доступно по адресу: [http://localhost:8000](http://localhost:8000)

---

## 🐳 Запуск через Docker

```bash
docker build -t emotion-analysis .
docker run -p 8000:8000 --env-file .env emotion-analysis
```

Или с помощью Docker Compose (если есть `docker-compose.yml`):

```bash
docker compose up --build
```

---

## 📁 Структура проекта

```
emotion-analysis-system/
│
├── backend/
│   ├── config.py                  # Все константы и переменные окружения
│   ├── main.py                    # Точка входа FastAPI
│   │
│   ├── database/
│   │   └── database.py            # DAL — все запросы к PostgreSQL
│   │
│   ├── model/
│   │   ├── emotion_model.py       # RuBERT + контекстная постобработка + расчёт выгорания
│   │   └── text_preprocessor.py   # Предобработка текста перед моделью
│   │
│   ├── routes/
│   │   ├── auth.py                # Авторизация, регистрация, выход
│   │   ├── dashboard.py           # /dashboard с роутингом по ролям
│   │   ├── api.py                 # /api/analyze, /api/team_analytics
│   │   ├── export.py              # /api/export_* (CSV)
│   │   └── deps.py                # FastAPI dependency: get_current_user
│   │
│   ├── services/
│   │   ├── emotion_service.py     # Бизнес-логика анализа эмоций
│   │   ├── export_service.py      # Генерация CSV-файлов
│   │   └── context_builders.py    # Контекст для Jinja2-шаблонов по ролям
│   │
│   ├── schemas/                   # Pydantic-модели для валидации
│   └── utils/
│       ├── formatting.py          # Форматирование дат и timestamp
│       └── keywords.py            # Извлечение ключевых слов из текста
│
├── templates/                     # HTML-шаблоны Jinja2
│   ├── layout.html                # Базовый layout
│   ├── login.html / register.html # Страницы аутентификации
│   ├── employee.html              # Дашборд сотрудника
│   ├── manager.html               # Дашборд руководителя
│   └── hr.html                    # Дашборд HR
│
├── static/css/
│   └── style.css                  # Дизайн-система проекта
│
├── tests/                         # Тесты
│   ├── conftest.py
│   ├── test_integration_api.py
│   ├── test_functional_api.py
│   ├── test_context_builders.py
│   ├── test_database_analytics.py
│   ├── test_export_service.py
│   ├── test_unit_text_preprocessing.py
│   └── test_ml_model_validation.py
│
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 🔌 API-эндпоинты

### Аутентификация

| Метод | Путь             | Описание                              | Доступ  |
|-------|------------------|---------------------------------------|---------|
| GET   | `/`              | Страница входа                        | Все     |
| POST  | `/api/login`     | Авторизация, устанавливает cookie     | Все     |
| POST  | `/api/logout`    | Выход из системы, удаляет cookie      | Все     |
| GET   | `/register`      | Страница регистрации                  | Все     |
| POST  | `/api/register`  | Создание нового аккаунта              | Все     |

### Основные

| Метод | Путь              | Описание                                         | Доступ        |
|-------|-------------------|--------------------------------------------------|---------------|
| GET   | `/dashboard`      | Главная страница (определяется по роли)           | Авторизованные |
| POST  | `/api/analyze`    | Анализ текста отчёта, сохранение результата      | Сотрудник     |
| GET   | `/api/team_analytics` | Динамика команды по периодам (JSON)          | Руководитель  |

### Экспорт (только HR)

| Метод | Путь                          | Параметры                                      | Описание              |
|-------|-------------------------------|------------------------------------------------|-----------------------|
| GET   | `/api/export_reports`         | `period` = all / month / quarter / year        | Сводный CSV по сотрудникам |
| GET   | `/api/export_detailed_reports`| `department`, `start_date`, `end_date`         | Детальный CSV с текстами отчётов |

#### Пример ответа `/api/analyze`

```json
{
  "success": true,
  "emotion": "Положительное состояние",
  "confidence": 0.91,
  "burnout_index": 0.12,
  "burnout_risk": "low",
  "burnout_trend": "stable"
}
```

---

## 🧪 Тесты

```bash
# Установить зависимости для тестов (если не установлены)
pip install pytest pytest-asyncio

# Запустить все тесты
pytest tests/ -v

# Запустить без ML-модели (только unit/integration)
pytest tests/ -v --ignore=tests/test_ml_model_validation.py
```

> Тесты используют моки для БД и ML-модели — реальное подключение не требуется.

---

## ⚙️ Переменные окружения

| Переменная     | Описание                            | Пример                                             |
|----------------|-------------------------------------|----------------------------------------------------|
| `DATABASE_URL` | Строка подключения к PostgreSQL     | `postgresql://user:pass@localhost:5432/emotion_db` |

---

## 🔒 Безопасность

- Сессии хранятся в БД с TTL 7 дней, передаются через `httponly` cookie
- Пароли хешируются через SHA-256
- Тексты отчётов сотрудников недоступны руководителям на уровне API
- Экспорт данных ограничен ролью HR-администратора

---

## 📄 Лицензия

MIT License — используйте свободно, ссылка на репозиторий приветствуется.