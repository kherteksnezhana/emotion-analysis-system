"""
Тесты для аналитических функций database.py
"""

import pytest
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock


class TestDatabaseAnalytics:
    """Тесты для аналитических функций БД (с моками)"""

    @patch('backend.database.database.get_db_connection')
    def test_get_user_burnout_trend_structure(self, mock_get_conn):
        """Проверка структуры возвращаемых данных get_user_burnout_trend"""
        from backend.database.database import get_user_burnout_trend

        # Мокаем соединение и курсор с поддержкой контекстного менеджера
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_get_conn.return_value = mock_conn

        # Мокаем результаты запроса
        mock_cursor.fetchall.return_value = [
            ("2025-05-15 10:00:00", 0.3),
            ("2025-05-14 10:00:00", 0.4),
            ("2025-05-13 10:00:00", 0.5),
        ]

        result = get_user_burnout_trend(user_id=1)

        assert "current" in result
        assert "trend" in result
        assert "history" in result
        assert isinstance(result["current"], float)
        assert isinstance(result["trend"], float)
        assert isinstance(result["history"], list)

        # Проверяем, что current — это самый последний отчет
        assert result["current"] == 0.3

    @patch('backend.database.database.get_db_connection')
    def test_get_user_burnout_trend_empty(self, mock_get_conn):
        """Проверка обработки пустого результата"""
        from backend.database.database import get_user_burnout_trend

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = []

        result = get_user_burnout_trend(user_id=1)

        assert result["current"] == 0.0
        assert result["trend"] == 0.0
        assert result["history"] == []

    @patch('backend.database.database.get_db_connection')
    def test_get_company_burnout_history_structure(self, mock_get_conn):
        """Проверка структуры данных истории выгорания компании"""
        from backend.database.database import get_company_burnout_history

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_get_conn.return_value = mock_conn

        # Мокаем результат запроса (как он приходит из БД)
        mock_cursor.fetchall.return_value = [
            ("2025-05-15", 0.25),
            ("2025-05-14", 0.30),
            ("2025-05-13", 0.28),
        ]

        result = get_company_burnout_history(days=30)

        # Проверяем структуру, а не конкретные значения
        assert isinstance(result, list)
        assert len(result) == 3
        assert "date" in result[0]
        assert "burnout" in result[0]
        assert isinstance(result[0]["date"], str)
        assert isinstance(result[0]["burnout"], float)

    @patch('backend.database.database.get_db_connection')
    def test_get_period_comparison_structure(self, mock_get_conn):
        """Проверка структуры данных сравнения периодов"""
        from backend.database.database import get_period_comparison

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [(75.0,), (65.0,)]

        result = get_period_comparison()

        assert "current" in result
        assert "previous" in result
        assert "change" in result
        assert "trend" in result
        assert isinstance(result["current"], (int, float))
        assert result["trend"] in ["up", "down", "stable"]

    @patch('backend.database.database.get_db_connection')
    def test_get_department_reports_stats_calculation(self, mock_get_conn):
        """Проверка расчета процентного распределения отчетов по отделам"""
        from backend.database.database import get_department_reports_stats

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchall.return_value = [
            ("IT", 150),
            ("Маркетинг", 100),
            ("Продажи", 50),
        ]

        result = get_department_reports_stats()

        total = 150 + 100 + 50
        assert result[0]["percentage"] == round((150 / total) * 100)
        assert result[1]["percentage"] == round((100 / total) * 100)
        assert result[2]["percentage"] == round((50 / total) * 100)

        # Сумма процентов должна быть близка к 100
        total_percentage = sum(r["percentage"] for r in result)
        assert abs(total_percentage - 100) <= 3

    @patch('backend.database.database.get_db_connection')
    def test_get_company_burnout_stats_high_burnout_filter(self, mock_get_conn):
        """Проверка фильтрации сотрудников с высоким выгоранием (>0.5)"""
        from backend.database.database import get_company_burnout_stats

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_get_conn.return_value = mock_conn

        # Первый запрос (avg) и второй запрос (high burnout employees)
        mock_cursor.fetchone.side_effect = [(0.45,), None]
        mock_cursor.fetchall.return_value = [
            (1, "Иванов Иван", "IT", 0.75),
            (2, "Петров Петр", "IT", 0.82),
        ]

        result = get_company_burnout_stats()

        assert "avg_burnout" in result
        assert "high_burnout_employees" in result
        assert len(result["high_burnout_employees"]) == 2
        assert result["high_burnout_employees"][0]["burnout"] == 0.75
        assert result["high_burnout_employees"][0]["name"] == "Иванов Иван"