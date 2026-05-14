from fastapi.responses import PlainTextResponse

import backend.database.database as db
import backend.routes.dashboard as dashboard_module
import backend.routes.export as export_module
from backend.services import export_service
from backend.services.context_builders import HRContextBuilder


def test_register_success_redirects(client, monkeypatch):
    monkeypatch.setattr(db, "add_user", lambda full_name, username, password, role, department: 42)

    response = client.post(
        "/api/register",
        data={
            "full_name": "Иван Иванов",
            "username": "ivanov",
            "password": "1234",
            "role": "Сотрудник",
            "department": "IT",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/?registered=success"


def test_logout_clears_session_cookie(client, monkeypatch):
    monkeypatch.setattr(db, "delete_session", lambda token: True)

    response = client.post("/api/logout", cookies={"session_token": "token123"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_dashboard_renders_template_for_hr(client, monkeypatch, sample_hr):
    monkeypatch.setattr(db, "get_session_by_token", lambda token: {"user_id": sample_hr["user_id"], "name": sample_hr["name"], "role": sample_hr["role"], "department": sample_hr["department"]})
    monkeypatch.setattr(HRContextBuilder, "build", lambda: {"employees_data": [], "dept_avg_scores": [], "emotion_stats": [], "company_burnout_history": [], "departments_burnout_history": [], "high_burnout_employees": []})
    monkeypatch.setattr(dashboard_module.templates, "TemplateResponse", lambda request, name, context: PlainTextResponse("dashboard", media_type="text/html"))

    response = client.get("/dashboard", cookies={"session_token": "token123"})
    assert response.status_code == 200
    assert response.text == "dashboard"


def test_export_reports_forbidden_for_non_hr(client, monkeypatch, sample_user):
    monkeypatch.setattr(db, "get_session_by_token", lambda token: {"user_id": sample_user["user_id"], "name": sample_user["name"], "role": sample_user["role"], "department": sample_user["department"]})

    response = client.get("/api/export_reports", cookies={"session_token": "token123"})
    assert response.status_code == 403


def test_export_detailed_reports_forbidden_for_non_hr(client, monkeypatch, sample_user):
    monkeypatch.setattr(db, "get_session_by_token", lambda token: {"user_id": sample_user["user_id"], "name": sample_user["name"], "role": sample_user["role"], "department": sample_user["department"]})

    response = client.get("/api/export_detailed_reports", cookies={"session_token": "token123"})
    assert response.status_code == 403


def test_export_reports_authorized_returns_csv(client, monkeypatch, sample_hr):
    monkeypatch.setattr(db, "get_session_by_token", lambda token: {"user_id": sample_hr["user_id"], "name": sample_hr["name"], "role": sample_hr["role"], "department": sample_hr["department"]})
    monkeypatch.setattr(export_service.ExportService, "build_summary_csv", staticmethod(lambda period="all": PlainTextResponse("col1;col2\nval1;val2", media_type="text/csv")))

    response = client.get("/api/export_reports", cookies={"session_token": "token123"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "col1;col2" in response.text


def test_export_detailed_reports_authorized_returns_csv(client, monkeypatch, sample_hr):
    monkeypatch.setattr(db, "get_session_by_token", lambda token: {"user_id": sample_hr["user_id"], "name": sample_hr["name"], "role": sample_hr["role"], "department": sample_hr["department"]})
    monkeypatch.setattr(export_service.ExportService, "build_detailed_csv", staticmethod(lambda department=None, start_date=None, end_date=None: PlainTextResponse("date;text\n2026-01-01;test", media_type="text/csv")))

    response = client.get("/api/export_detailed_reports", cookies={"session_token": "token123"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "date;text" in response.text
