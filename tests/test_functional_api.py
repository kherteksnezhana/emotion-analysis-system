"""
Функциональные тесты API и основных роутов.
"""

import pytest
from fastapi.responses import PlainTextResponse

from backend.database import database as db
from backend.services.context_builders import HRContextBuilder


# ====================== AUTH ======================

def test_register_success(client, monkeypatch):
    """Успешная регистрация"""
    monkeypatch.setattr(db, "add_user", lambda *args, **kwargs: 999)

    response = client.post(
        "/api/register",
        data={
            "full_name": "Тестовый Пользователь",
            "username": "testuser",
            "password": "1234",
            "role": "Сотрудник",
            "department": "IT",
        },
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert "/?registered=success" in response.headers.get("location", "")


def test_register_existing_user(client, monkeypatch):
    """Попытка регистрации уже существующего пользователя"""
    monkeypatch.setattr(db, "add_user", lambda *args, **kwargs: None)

    response = client.post(
        "/api/register",
        data={
            "full_name": "Существующий",
            "username": "existing",
            "password": "1234",
            "role": "Сотрудник",
            "department": "IT",
        },
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert "error=user_exists" in response.headers.get("location", "")


def test_login_success(client, monkeypatch, sample_user):
    """Успешный вход"""
    monkeypatch.setattr(db, "get_user_by_username", lambda *args, **kwargs: sample_user)
    monkeypatch.setattr(db, "create_session", lambda *args, **kwargs: "test_session_token_123")

    response = client.post(
        "/api/login",
        data={"username": "testuser", "password": "1234"},
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert "/" in response.headers.get("location", "")


def test_logout(client, monkeypatch):
    """Выход из системы"""
    monkeypatch.setattr(db, "delete_session", lambda *args, **kwargs: True)

    response = client.post(
        "/api/logout",
        cookies={"session_token": "valid_token"},
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert "/" in response.headers.get("location", "")


# ====================== DASHBOARD ======================

def test_dashboard_redirects_unauthorized(client):
    """Неавторизованный пользователь перенаправляется на логин"""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert "/login" in response.headers.get("location", "")


def test_employee_dashboard(client, monkeypatch, sample_user):
    """Даашборд обычного сотрудника"""
    monkeypatch.setattr(db, "get_session_by_token", lambda *args, **kwargs: sample_user)

    # Мокаем рендер шаблона
    from backend.routes.dashboard import templates
    monkeypatch.setattr(templates, "TemplateResponse",
                        lambda *args, **kwargs: PlainTextResponse("employee_dashboard"))

    response = client.get("/dashboard", cookies={"session_token": "valid_token"})
    assert response.status_code == 200


def test_hr_dashboard(client, monkeypatch, sample_hr):
    """Даашборд HR-администратора"""
    monkeypatch.setattr(db, "get_session_by_token", lambda *args, **kwargs: sample_hr)

    monkeypatch.setattr(HRContextBuilder, "build",
                        lambda *args, **kwargs: {"employees_data": [], "dept_avg_scores": []})

    from backend.routes.dashboard import templates
    monkeypatch.setattr(templates, "TemplateResponse",
                        lambda *args, **kwargs: PlainTextResponse("hr_dashboard"))

    response = client.get("/dashboard", cookies={"session_token": "valid_token"})
    assert response.status_code == 200


# ====================== EXPORT ======================

def test_export_reports_forbidden_for_employee(client, monkeypatch, sample_user):
    """Обычный сотрудник не может экспортировать отчёты"""
    monkeypatch.setattr(db, "get_session_by_token", lambda *args, **kwargs: sample_user)

    response = client.get("/api/export_reports", cookies={"session_token": "valid_token"})
    assert response.status_code == 403


def test_export_detailed_reports_forbidden_for_employee(client, monkeypatch, sample_user):
    """Обычный сотрудник не может экспортировать детальные отчёты"""
    monkeypatch.setattr(db, "get_session_by_token", lambda *args, **kwargs: sample_user)

    response = client.get("/api/export_detailed_reports", cookies={"session_token": "valid_token"})
    assert response.status_code == 403


def test_export_reports_allowed_for_hr(client, monkeypatch, sample_hr):
    """HR может экспортировать отчёты"""
    monkeypatch.setattr(db, "get_session_by_token", lambda *args, **kwargs: sample_hr)
    monkeypatch.setattr(db, "get_all_reports_for_export", lambda *args, **kwargs: [])

    response = client.get("/api/export_reports", cookies={"session_token": "valid_token"})
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")


# ====================== REPORT SUBMISSION ======================

def test_submit_report_success(client, monkeypatch, sample_user):
    """Успешная отправка отчёта"""
    monkeypatch.setattr(db, "get_session_by_token", lambda *args, **kwargs: sample_user)
    monkeypatch.setattr(db, "save_report", lambda *args, **kwargs: 777)
    monkeypatch.setattr(db, "save_analysis_result", lambda *args, **kwargs: None)

    response = client.post(
        "/api/submit_report",
        data={"report_text": "Сегодня продуктивно работал над задачами."},
        cookies={"session_token": "valid_token"},
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    assert "report_submitted=success" in response.headers.get("location", "")


# ====================== FIXTURES (если нужно) ======================

@pytest.fixture
def sample_user():
    return {
        "id": 1,
        "username": "testuser",
        "role": "Сотрудник",
        "department": "IT",
        "full_name": "Тестовый Пользователь"
    }


@pytest.fixture
def sample_hr():
    return {
        "id": 2,
        "username": "hr_admin",
        "role": "HR-администратор",
        "department": "HR",
        "full_name": "Марина Иванова"
    }