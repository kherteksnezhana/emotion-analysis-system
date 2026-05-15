"""
Тесты для построителей контекста (EmployeeContextBuilder, ManagerContextBuilder, HRContextBuilder)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Импортируем классы для тестирования
from backend.services.context_builders import (
    EmployeeContextBuilder,
    ManagerContextBuilder,
    HRContextBuilder,
)


class TestEmployeeContextBuilder:
    """Тесты для EmployeeContextBuilder"""
    
    @patch('backend.services.context_builders.db')
    def test_build_returns_required_keys(self, mock_db):
        """Проверка, что build() возвращает все необходимые ключи"""
        # Мокаем данные
        mock_db.get_user_reports.return_value = []
        mock_db.get_user_weighted_wellbeing.return_value = 75.0
        mock_db.get_user_score_trend.return_value = {"trend": "up", "change": 5}
        mock_db.get_user_burnout_trend.return_value = {"current": 0.3, "trend": 0.02}
        
        result = EmployeeContextBuilder.build(user_id=1)
        
        required_keys = ["reports", "avg_score", "score_trend", "current_emotion", 
                         "burnout_current", "burnout_trend", "burnout_trend_percent"]
        for key in required_keys:
            assert key in result, f"Key '{key}' missing in result"
    
    @patch('backend.services.context_builders.db')
    def test_build_with_reports(self, mock_db):
        """Проверка обработки отчетов"""
        mock_reports = [
            {
                "id": 1,
                "text": "Отличный день!",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "emotion": "Положительное состояние",
                "confidence": 0.9,
                "burnout_index": 0.1,
            }
        ]
        mock_db.get_user_reports.return_value = mock_reports
        mock_db.get_user_weighted_wellbeing.return_value = 85.0
        mock_db.get_user_score_trend.return_value = None
        mock_db.get_user_burnout_trend.return_value = {"current": 0.15, "trend": -0.05}
        
        result = EmployeeContextBuilder.build(user_id=1)
        
        assert len(result["reports"]) == 1
        assert "timestamp" in result["reports"][0]
        assert "keywords" in result["reports"][0]
        assert result["avg_score"] == 85
        assert result["current_emotion"] == "Положительное состояние"
        assert result["burnout_trend_percent"] == -5
    
    @patch('backend.services.context_builders.db')
    def test_build_without_reports(self, mock_db):
        """Проверка обработки случая без отчетов"""
        mock_db.get_user_reports.return_value = []
        mock_db.get_user_weighted_wellbeing.return_value = 50.0
        mock_db.get_user_score_trend.return_value = None
        mock_db.get_user_burnout_trend.return_value = {"current": 0.0, "trend": 0.0}
        
        result = EmployeeContextBuilder.build(user_id=1)
        
        assert result["reports"] == []
        assert result["current_emotion"] is None
        assert result["burnout_trend_percent"] == 0


class TestManagerContextBuilder:
    """Тесты для ManagerContextBuilder"""
    
    @patch('backend.services.context_builders.db')
    def test_build_returns_required_keys(self, mock_db):
        """Проверка, что build() возвращает все необходимые ключи"""
        mock_db.get_team_with_reports.return_value = []
        mock_db.get_all_team_reports.return_value = []
        mock_db.get_user_weighted_score.return_value = 75.0
        mock_db.get_user_score_trend.return_value = None
        mock_db.get_user_burnout_trend.return_value = {"current": 0.2}
        
        user = {"id": 1, "name": "Manager", "role": "Руководитель", "department": "IT"}
        
        result = ManagerContextBuilder.build(user)
        
        required_keys = ["team", "all_reports", "avg_score", "chart_labels", "chart_data",
                         "dist_data", "stats_excellent", "stats_good", "stats_warning",
                         "top_keywords", "total_employees", "reported_today", 
                         "not_reported_today", "reports_percentage", "team_burnout"]
        for key in required_keys:
            assert key in result, f"Key '{key}' missing in result"
    
    @patch('backend.services.context_builders.db')
    def test_build_calculates_avg_score_correctly(self, mock_db):
        """Проверка расчета среднего балла по команде"""
        team_members = [
            {"id": 1, "full_name": "User1", "has_reports": True, "weighted_score": 90},
            {"id": 2, "full_name": "User2", "has_reports": True, "weighted_score": 70},
            {"id": 3, "full_name": "User3", "has_reports": True, "weighted_score": 80},
        ]
        mock_db.get_team_with_reports.return_value = team_members
        mock_db.get_all_team_reports.return_value = []

        # Мокаем методы, вызываемые для каждого члена команды
        def mock_weighted_score(user_id):
            return next(m["weighted_score"] for m in team_members if m["id"] == user_id)

        def mock_score_trend(user_id):
            return None

        def mock_burnout_trend(user_id):
            return {"current": 0.2}  # Добавляем мок для выгорания

        mock_db.get_user_weighted_score.side_effect = mock_weighted_score
        mock_db.get_user_score_trend.side_effect = mock_score_trend
        mock_db.get_user_burnout_trend.side_effect = mock_burnout_trend  # Добавить эту строку

        user = {"id": 1, "name": "Manager", "role": "Руководитель", "department": "IT"}

        result = ManagerContextBuilder.build(user)

        expected_avg = (90 + 70 + 80) / 3
        assert result["avg_score"] == int(expected_avg)
    
    @patch('backend.services.context_builders.db')
    def test_build_filters_text_from_reports(self, mock_db):
        """Проверка, что тексты отчетов не передаются на клиент"""
        reports_with_text = [
            {
                "user_id": 1,
                "text": "Секретный текст отчета",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "emotion": "positive",
                "confidence": 0.9,
                "burnout_index": 0.1,
            }
        ]
        mock_db.get_all_team_reports.return_value = reports_with_text
        mock_db.get_team_with_reports.return_value = []
        mock_db.get_user_weighted_score.return_value = 75.0
        mock_db.get_user_score_trend.return_value = None
        mock_db.get_user_burnout_trend.return_value = {"current": 0.2}
        
        user = {"id": 1, "name": "Manager", "role": "Руководитель", "department": "IT"}
        
        result = ManagerContextBuilder.build(user)
        
        # Проверяем, что тексты отсутствуют в all_reports
        for report in result["all_reports"]:
            assert "text" not in report


class TestHRContextBuilder:
    """Тесты для HRContextBuilder"""
    
    @patch('backend.services.context_builders.db')
    def test_build_returns_required_keys(self, mock_db):
        """Проверка, что build() возвращает все необходимые ключи"""
        mock_db.get_all_users.return_value = []
        mock_db.get_user_reports.return_value = []
        mock_db.get_user_weighted_score.return_value = 0.0
        mock_db.get_user_score_trend.return_value = None
        mock_db.get_company_burnout_history.return_value = []
        mock_db.get_departments_burnout_history.return_value = {}
        mock_db.get_company_burnout_stats.return_value = {"high_burnout_employees": []}
        mock_db.get_period_comparison.return_value = {"current": 70, "previous": 65, "change": 5}
        mock_db.get_department_reports_stats.return_value = []
        
        result = HRContextBuilder.build()
        
        required_keys = ["total_employees", "total_reports", "current_month_ru", 
                         "need_attention_count", "high_morale_count", "employees_data",
                         "departments", "emotion_stats", "dept_avg_scores", 
                         "avg_company_score", "company_burnout_history", 
                         "company_burnout_avg", "high_burnout_employees"]
        for key in required_keys:
            assert key in result, f"Key '{key}' missing in result"
    
    @patch('backend.services.context_builders.db')
    def test_build_calculates_need_attention_correctly(self, mock_db):
        """Проверка правильности подсчета сотрудников, требующих внимания"""
        users = [
            {"id": 1, "full_name": "User1", "role": "Сотрудник", "department": "IT"},
            {"id": 2, "full_name": "User2", "role": "Сотрудник", "department": "IT"},
            {"id": 3, "full_name": "User3", "role": "Сотрудник", "department": "IT"},
        ]
        
        reports_map = {
            1: [{"emotion": "positive", "burnout_index": 0.2, "confidence": 0.9}],
            2: [{"emotion": "negative", "burnout_index": 0.6, "confidence": 0.4}],  # требует внимания
            3: [],  # нет отчетов
        }
        
        weighted_scores = {1: 85, 2: 45, 3: 0}
        
        def mock_get_all_users():
            return users
        
        def mock_get_user_reports(user_id):
            return reports_map.get(user_id, [])
        
        def mock_get_user_weighted_score(user_id):
            return weighted_scores.get(user_id, 0)
        
        mock_db.get_all_users.side_effect = mock_get_all_users
        mock_db.get_user_reports.side_effect = mock_get_user_reports
        mock_db.get_user_weighted_score.side_effect = mock_get_user_weighted_score
        mock_db.get_user_score_trend.return_value = None
        mock_db.get_company_burnout_history.return_value = []
        mock_db.get_departments_burnout_history.return_value = {}
        mock_db.get_company_burnout_stats.return_value = {"high_burnout_employees": []}
        mock_db.get_period_comparison.return_value = {"current": 70, "previous": 65, "change": 5}
        mock_db.get_department_reports_stats.return_value = []
        
        result = HRContextBuilder.build()
        
        # User2 имеет weighted_score 45 (<60) — требует внимания
        assert result["need_attention_count"] == 1
        assert result["total_employees"] == 3