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