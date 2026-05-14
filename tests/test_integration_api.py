import datetime

import pytest
from fastapi.responses import PlainTextResponse

import backend.database.database as db
import backend.routes.api as api_module


def test_login_success_redirects_and_sets_cookie(client, monkeypatch):
    def fake_verify_user(username, password):
        return (1, "Тестовый пользователь", "Сотрудник", "IT")

    def fake_save_session(user_id, token, days):
        return True

    monkeypatch.setattr(db, "verify_user", fake_verify_user)
    monkeypatch.setattr(db, "save_session", fake_save_session)

    response = client.post("/api/login", data={"username": "user1", "password": "pass1"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert "session_token" in response.headers.get("set-cookie", "")


def test_login_failure_redirects_to_error(client, monkeypatch):
    monkeypatch.setattr(db, "verify_user", lambda username, password: None)

    response = client.post("/api/login", data={"username": "user1", "password": "wrong"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/?error=auth"


def test_analyze_valid_text_returns_success(client, monkeypatch, sample_user):
    monkeypatch.setattr(db, "get_session_by_token", lambda token: {"user_id": sample_user["user_id"], "name": sample_user["name"], "role": sample_user["role"], "department": sample_user["department"]})
    monkeypatch.setattr(db, "get_user_reports_history", lambda user_id, limit=10: [])
    monkeypatch.setattr(db, "save_report", lambda user_id, text: 123)
    monkeypatch.setattr(db, "save_analysis_result", lambda report_id, emotion_label, confidence, burnout_index, all_scores: True)

    import backend.services.emotion_service as emotion_service

    monkeypatch.setattr(
        emotion_service,
        "analyze_emotion",
        lambda text, user_history=None: {
            "display_label": "Положительное состояние",
            "score": 0.92,
            "all_scores": {"positive": 0.92, "neutral": 0.06, "negative": 0.02},
            "burnout_index": 0.12,
            "burnout_risk": "low",
            "burnout_trend": "stable",
        },
    )

    response = client.post(
        "/api/analyze",
        data={"text": "Сегодня отличный день, работа шла гладко."},
        cookies={"session_token": "token123"},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["emotion"] == "Положительное состояние"


def test_analyze_short_text_rejects_short_content(client, monkeypatch, sample_user):
    monkeypatch.setattr(db, "get_session_by_token", lambda token: {"user_id": sample_user["user_id"], "name": sample_user["name"], "role": sample_user["role"], "department": sample_user["department"]})
    monkeypatch.setattr(db, "get_user_reports_history", lambda user_id, limit=10: [])

    response = client.post("/api/analyze", data={"text": "Коротко."}, cookies={"session_token": "token123"})
    assert response.status_code == 400
    assert "слишком короткий" in response.json()["detail"].lower()


def test_team_analytics_forbidden_for_non_manager(client, monkeypatch, sample_user):
    monkeypatch.setattr(db, "get_session_by_token", lambda token: {"user_id": sample_user["user_id"], "name": sample_user["name"], "role": sample_user["role"], "department": sample_user["department"]})

    response = client.get("/api/team_analytics", cookies={"session_token": "token123"})
    assert response.status_code == 403


def test_team_analytics_for_manager_returns_data(client, monkeypatch, sample_manager):
    now = datetime.datetime.now()
    sample_report = {
        "user_id": 10,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "confidence": 0.8,
    }

    monkeypatch.setattr(db, "get_session_by_token", lambda token: {"user_id": sample_manager["user_id"], "name": sample_manager["name"], "role": sample_manager["role"], "department": sample_manager["department"]})
    monkeypatch.setattr(db, "get_all_team_reports", lambda department: [sample_report])
    monkeypatch.setattr(db, "calculate_weighted_score_for_list", lambda reports_list: 0.8)

    response = client.get("/api/team_analytics?period=week", cookies={"session_token": "token123"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "week"
    assert isinstance(payload["labels"], list)
    assert isinstance(payload["values"], list)
