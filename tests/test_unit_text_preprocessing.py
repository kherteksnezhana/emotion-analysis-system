import importlib
import pytest
import transformers

from backend.model.text_preprocessor import preprocess_for_model


@pytest.fixture(autouse=True)
def patch_transformers_pipeline(monkeypatch):
    """Мокируем загрузку transformers.pipeline для быстрых unit-тестов."""
    monkeypatch.setattr(transformers, "pipeline", lambda *args, **kwargs: None)

    # Перезагружаем модуль emotion_model после мокинга
    import backend.model.emotion_model as emotion_model
    importlib.reload(emotion_model)
    yield


def test_preprocess_for_model_replaces_numbers_and_keeps_punctuation():
    text = "Привет! Сегодня 123 задачи выполнены."
    result = preprocess_for_model(text)

    assert "<NUM>" in result
    assert result.startswith("привет!")
    assert "задачи" in result
    assert "выполнены." in result


def test_preprocess_for_model_handles_empty_and_short_text():
    assert preprocess_for_model("") == ""
    assert preprocess_for_model("   ") == ""
    assert len(preprocess_for_model("Короткий")) > 0


def test_analyze_emotion_returns_correct_structure():
    """Проверяем новый интерфейс analyze_emotion после обновлений"""
    from backend.model.emotion_model import analyze_emotion

    text = "Отличный день! Закрыл сделку на миллион."
    result = analyze_emotion(text)

    assert isinstance(result, dict)
    assert "label" in result
    assert "display_label" in result
    assert "score" in result
    assert "all_scores" in result
    assert "burnout_index" in result
    assert "burnout_risk" in result
    assert result["label"] in {"positive", "neutral", "negative"}
    assert 0.0 <= result["score"] <= 1.0
    assert 0.0 <= result["burnout_index"] <= 1.0


def test_burnout_keywords_detection():
    """Проверяем работу семантического детектора выгорания"""
    from backend.model.emotion_model import _detect_burnout_keywords

    negative_text = "Сил нет. Я устал и хочу уволиться. Постоянное выгорание."
    score = _detect_burnout_keywords(negative_text)

    assert score > 0.3  # должно быть заметное выгорание


def test_context_correction_works():
    """Проверяем, что analyze_emotion работает без ошибок"""
    from backend.model.emotion_model import analyze_emotion

    success_text = "Прорыв! Перевыполнил план и закрыл крупную сделку."
    result = analyze_emotion(success_text)

    assert isinstance(result, dict)
    assert "label" in result
    assert "burnout_index" in result


def test_calculate_weighted_score():
    """Тест функции взвешенного среднего с экспоненциальным затуханием"""
    from backend.database.database import calculate_weighted_score

    # Создаем тестовые отчеты с разными датами и confidence
    reports = [
        {"timestamp": "2025-05-15 10:00:00", "confidence": 0.9},
        {"timestamp": "2025-05-14 10:00:00", "confidence": 0.7},
        {"timestamp": "2025-05-13 10:00:00", "confidence": 0.5},
    ]

    result = calculate_weighted_score(reports, decay_factor=0.7)

    # Проверяем, что результат в диапазоне [0, 1]
    assert 0.0 <= result <= 1.0

    # Проверяем, что более свежий отчет имеет больший вес
    # confidence=0.9 (самый свежий) должен влиять больше, чем 0.5
    assert result > 0.6

    # Проверяем обработку пустого списка
    assert calculate_weighted_score([]) == 0.0

    # Проверяем с одним отчетом
    single_report = [{"timestamp": "2025-05-15 10:00:00", "confidence": 0.8}]
    assert calculate_weighted_score(single_report) == 0.8


def test_calculate_weighted_score_decay_factor():
    """Тест влияния коэффициента затухания на результат"""
    from backend.database.database import calculate_weighted_score

    reports = [
        {"timestamp": "2025-05-15 10:00:00", "confidence": 1.0},  # свежий
        {"timestamp": "2025-05-14 10:00:00", "confidence": 0.0},  # старый
    ]

    # При высоком коэффициенте затухания (0.9) свежий отчет имеет очень большой вес
    # Веса: 1.0 (свежий) и 0.9 (старый) -> weighted = (1.0*1.0 + 0.0*0.9) / (1.0+0.9) = 1.0/1.9 ≈ 0.526
    high_decay = calculate_weighted_score(reports, decay_factor=0.9)
    assert 0.5 < high_decay < 0.55  # ~0.526

    # При низком коэффициенте затухания (0.3) веса более равномерны
    # Веса: 1.0 (свежий) и 0.3 (старый) -> weighted = (1.0*1.0 + 0.0*0.3) / (1.0+0.3) = 1.0/1.3 ≈ 0.769
    low_decay = calculate_weighted_score(reports, decay_factor=0.3)
    assert 0.76 < low_decay < 0.78  # ~0.769


def test_parse_scores():
    """Тест парсинга выходных данных модели RuBERT"""
    from backend.model.emotion_model import _parse_scores

    # Тестируем корректный формат вывода
    mock_output = [[
        {"label": "POSITIVE", "score": 0.85},
        {"label": "NEUTRAL", "score": 0.10},
        {"label": "NEGATIVE", "score": 0.05},
    ]]

    result = _parse_scores(mock_output)

    assert "positive" in result
    assert "neutral" in result
    assert "negative" in result
    assert abs(result["positive"] + result["neutral"] + result["negative"] - 1.0) < 0.01
    assert result["positive"] == 0.85

    # Тестируем альтернативный формат вывода (без вложенного списка)
    mock_output_alt = [
        {"label": "NEUTRAL", "score": 0.60},
        {"label": "POSITIVE", "score": 0.30},
        {"label": "NEGATIVE", "score": 0.10},
    ]

    result_alt = _parse_scores(mock_output_alt)
    assert abs(result_alt["neutral"] - 0.60) < 0.01

    # Тестируем пустой вывод
    assert _parse_scores([]) == {"positive": 0.0, "neutral": 0.0, "negative": 0.0}


def test_detect_markers():
    """Тест детекции маркеров успеха/негатива в тексте"""
    from backend.model.emotion_model import _detect_markers
    from backend.config import POSITIVE_SUCCESS_MARKERS, NEGATIVE_CONTEXT_MARKERS

    # Тестируем позитивные маркеры
    positive_text = "Сегодня я успешно закрыл сделку! Отличный результат!"
    pos_score = _detect_markers(positive_text, POSITIVE_SUCCESS_MARKERS)
    assert pos_score > 0.1

    # Тестируем негативные маркеры
    negative_text = "Я полностью выгорел. Нет сил совсем, опускаются руки."
    neg_score = _detect_markers(negative_text, NEGATIVE_CONTEXT_MARKERS)
    assert neg_score > 0.3

    # Тестируем пустой текст
    assert _detect_markers("", POSITIVE_SUCCESS_MARKERS) == 0.0

    # Тестируем текст без маркеров
    neutral_text = "Сегодня работал над задачами. Все по плану."
    neutral_score = _detect_markers(neutral_text, POSITIVE_SUCCESS_MARKERS)
    assert neutral_score == 0.0


def test_historical_burnout():
    """Тест расчета исторического фактора выгорания"""
    from backend.model.emotion_model import _historical_burnout

    # Тестируем с историей
    history = [
        {"burnout_index": 0.3},
        {"burnout_index": 0.5},
        {"burnout_index": 0.4},
    ]

    result = _historical_burnout(history)
    expected = (0.3 + 0.5 + 0.4) / 3
    assert abs(result - expected) < 0.01

    # Тестируем с пустой историей
    assert _historical_burnout([]) == 0.0

    # Тестируем с None
    assert _historical_burnout(None) == 0.0

    # Тестируем с историей, где есть None значения
    history_with_none = [
        {"burnout_index": 0.3},
        {"burnout_index": None},
        {"burnout_index": 0.5},
    ]
    result = _historical_burnout(history_with_none)
    expected = (0.3 + 0.5) / 2
    assert abs(result - expected) < 0.01


def test_calculate_burnout():
    """Тест комплексного расчета индекса выгорания"""
    from backend.model.emotion_model import _calculate_burnout

    # Тестируем с высоким негативом
    scores_high_negative = {"positive": 0.1, "neutral": 0.2, "negative": 0.7}
    text_negative = "Я устал и выгорел"
    result = _calculate_burnout(scores_high_negative, text_negative, None)

    assert "burnout_index" in result
    assert "risk_level" in result
    assert 0.0 <= result["burnout_index"] <= 1.0

    # Высокий негатив + маркеры выгорания должны дать высокий индекс
    assert result["burnout_index"] > 0.5

    # Тестируем с высоким позитивом
    scores_high_positive = {"positive": 0.9, "neutral": 0.05, "negative": 0.05}
    text_positive = "Отличный продуктивный день!"
    result_positive = _calculate_burnout(scores_high_positive, text_positive, None)
    assert result_positive["burnout_index"] < 0.3