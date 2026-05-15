"""
Тесты для сервиса экспорта данных (ExportService)
"""

import pytest
import asyncio
from unittest.mock import patch, Mock


class TestExportService:
    """Тесты для ExportService"""

    async def _get_response_content(self, response):
        """Вспомогательная функция для получения содержимого StreamingResponse"""
        content = b""
        async for chunk in response.body_iterator:
            content += chunk
        return content.decode("utf-8-sig")

    @patch('backend.services.export_service.db')
    def test_build_summary_csv_structure(self, mock_db):
        """Проверка структуры CSV-файла (заголовки, кодировка)"""
        from backend.services.export_service import ExportService
        import asyncio

        # Мокаем данные
        mock_users = [
            {"id": 1, "full_name": "Иванов Иван", "department": "IT", "role": "Сотрудник"},
            {"id": 2, "full_name": "Петров Петр", "department": "IT", "role": "Сотрудник"},
        ]
        mock_db.get_all_users.return_value = mock_users

        def mock_get_user_reports(user_id):
            if user_id == 1:
                return [{"emotion": "positive", "timestamp": "2025-05-15 10:00:00"}]
            return [{"emotion": "neutral", "timestamp": "2025-05-14 10:00:00"}]

        def mock_get_user_weighted_score(user_id):
            return 75.0 if user_id == 1 else 65.0

        def mock_get_user_burnout_trend(user_id):
            return {"current": 0.2, "trend": -0.05}

        mock_db.get_user_reports.side_effect = mock_get_user_reports
        mock_db.get_user_weighted_score.side_effect = mock_get_user_weighted_score
        mock_db.get_user_burnout_trend.side_effect = mock_get_user_burnout_trend

        response = ExportService.build_summary_csv(period="all")

        # Проверяем MIME-тип
        assert response.media_type == "text/csv"

        # Проверяем заголовок Content-Disposition
        assert "attachment; filename=" in response.headers["Content-Disposition"]
        assert ".csv" in response.headers["Content-Disposition"]

        # Получаем содержимое синхронно через asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        content = loop.run_until_complete(self._get_response_content(response))
        loop.close()

        # Проверяем наличие заголовков
        expected_headers = ["ФИО", "Отдел", "Всего отчётов", "Средний балл (взвешенный)",
                           "Последняя эмоция", "Индекс выгорания (%)", "Тренд выгорания"]
        for header in expected_headers:
            assert header in content

    @patch('backend.services.export_service.db')
    def test_build_summary_csv_calculates_burnout_trend_correctly(self, mock_db):
        """Проверка правильности расчета тренда выгорания"""
        from backend.services.export_service import ExportService
        import asyncio

        mock_users = [
            {"id": 1, "full_name": "Тестовый", "department": "IT", "role": "Сотрудник"},
        ]
        mock_db.get_all_users.return_value = mock_users
        mock_db.get_user_reports.return_value = [{"emotion": "positive", "timestamp": "2025-05-15 10:00:00"}]
        mock_db.get_user_weighted_score.return_value = 80.0

        # Тестируем разные тренды
        trends = [
            (0.3, 0.1, "↑"),   # рост выгорания
            (0.3, -0.1, "↓"),  # снижение выгорания
            (0.3, 0.0, "→"),   # стабильно
        ]

        for current, trend_change, expected_icon in trends:
            mock_db.get_user_burnout_trend.return_value = {"current": current, "trend": trend_change}

            response = ExportService.build_summary_csv(period="all")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            content = loop.run_until_complete(self._get_response_content(response))
            loop.close()

            # Проверяем, что тренд отображается корректно
            assert expected_icon in content

    @patch('backend.services.export_service.db')
    def test_build_detailed_csv_content(self, mock_db):
        """Проверка содержимого детального CSV-отчета"""
        from backend.services.export_service import ExportService
        import asyncio

        # Мокаем список пользователей
        mock_users = [
            {"id": 1, "full_name": "Иванов Иван", "department": "IT", "role": "Сотрудник"},
        ]
        mock_db.get_all_users.return_value = mock_users

        # Мокаем отчеты для пользователя
        mock_reports = [
            {
                "text": "Сегодня работал над проектом",
                "timestamp": "2025-05-15 10:30:00",
                "emotion": "positive",
                "confidence": 0.95,
                "burnout_index": 0.1,
            }
        ]
        mock_db.get_user_reports.return_value = mock_reports

        response = ExportService.build_detailed_csv(department="IT")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        content = loop.run_until_complete(self._get_response_content(response))
        loop.close()

        # Проверяем, что CSV содержит данные
        # (заголовки должны быть, даже если данных нет в этом тесте)
        assert "Дата" in content
        assert "Время" in content
        assert "Сотрудник" in content
        assert "Отдел" in content
        assert "Текст отчёта" in content

    @patch('backend.services.export_service.db')
    def test_build_detailed_csv_date_validation(self, mock_db):
        """Проверка валидации дат в детальном экспорте"""
        from backend.services.export_service import ExportService
        from fastapi import HTTPException
        from datetime import datetime

        mock_users = []
        mock_db.get_all_users.return_value = mock_users

        # Тестируем дату начала в будущем (должна вызвать ошибку)
        future_date = (datetime.now().year + 1, datetime.now().month, datetime.now().day)
        start_date = f"{future_date[0]}-{future_date[1]:02d}-{future_date[2]:02d}"

        with pytest.raises(HTTPException) as exc_info:
            ExportService.build_detailed_csv(start_date=start_date)
        assert exc_info.value.status_code == 400
        assert "будущем" in str(exc_info.value.detail)

        # Тестируем дату начала позже даты окончания
        with pytest.raises(HTTPException) as exc_info2:
            ExportService.build_detailed_csv(start_date="2025-05-20", end_date="2025-05-10")
        assert exc_info2.value.status_code == 400