# Emotion Analysis System

**Платформа для анализа эмоционального состояния сотрудников** на основе текстовых ежедневных отчётов с помощью RuBERT.

---

## Стек технологий

| Компонент       | Технология                                      |
|-----------------|-------------------------------------------------|
| Backend         | FastAPI + Uvicorn                               |
| ML-модель       | MonoHime/rubert-base-cased-sentiment-new (Hugging Face) |
| База данных     | PostgreSQL + psycopg2 (connection pool)         |
| Шаблоны         | Jinja2                                          |
| Frontend        | Vanilla JS + Chart.js + Flatpickr + Lucide Icons |
| Контейнеризация | Docker                                          |

---

## Роли пользователей

- **Сотрудник** — пишет ежедневные отчёты, видит свою личную аналитику и уровень риска выгорания.
- **Руководитель** — видит сводку по своему отделу и команде (без доступа к текстам отчётов).
- **HR-администратор** — полная аналитика по всей компании + экспорт данных в CSV.

---

## Структура проекта

```bash
backend/
├── config.py                  # Все настройки и константы
├── main.py                    # Точка входа FastAPI
├── database/
│   └── database.py            # DAL (все запросы к БД)
├── model/
│   ├── emotion_model.py       # Загрузка и работа с RuBERT + расчёт выгорания
│   └── text_preprocessor.py   # Предобработка текста
├── routes/
│   ├── auth.py                # Авторизация и регистрация
│   ├── dashboard.py           # Главная страница (роутинг по ролям)
│   ├── api.py                 # API-эндпоинты анализа
│   ├── export.py              # Экспорт отчётов
│   └── deps.py                # Зависимости (get_current_user)
├── services/
│   ├── emotion_service.py     # Основная бизнес-логика анализа
│   ├── export_service.py      # Генерация CSV
│   └── context_builders.py    # Контекст для Jinja2-шаблонов
├── schemas/                   # Pydantic-модели
├── utils/
│   ├── formatting.py          # Форматирование дат и т.д.
│   └── keywords.py            # Работа с ключевыми словами
├── __init__.py
│
templates/                     # HTML-шаблоны Jinja2
static/css/                    # Стили
tests/                         # Тесты