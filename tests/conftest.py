import os
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для стабильного импорта пакета backend.
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Поддержка запуска тестов без заранее заданного DATABASE_URL.
# Если настоящая БД не настроена, всё же даём возможность импортировать конфигурацию и мокать вызовы.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://placeholder:placeholder@localhost:5432/placeholder_db",
)

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes import auth_router, dashboard_router, api_router, export_router


@pytest.fixture(scope="session")
def app():
    application = FastAPI()
    application.include_router(auth_router)
    application.include_router(dashboard_router)
    application.include_router(api_router)
    application.include_router(export_router)
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def sample_user():
    return {"user_id": 1, "name": "Тестовый пользователь", "role": "Сотрудник", "department": "IT"}


@pytest.fixture
def sample_manager():
    return {"user_id": 2, "name": "Менеджер", "role": "Руководитель", "department": "IT"}


@pytest.fixture
def sample_hr():
    return {"user_id": 3, "name": "HR", "role": "HR-администратор", "department": "HR"}
