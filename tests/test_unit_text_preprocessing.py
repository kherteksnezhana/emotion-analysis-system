import importlib

import pytest
import transformers

from backend.model.text_preprocessor import preprocess_for_model, postprocess_sentiment_scores


@pytest.fixture(autouse=True)
def patch_transformers_pipeline(monkeypatch):
    """Мокируем загрузку transformers.pipeline для быстрых unit-тестов."""
    monkeypatch.setattr(transformers, "pipeline", lambda *args, **kwargs: None)
    # Перезагружаем модуль, чтобы избежать долгой инициализации модели RuBERT.
    import backend.model.emotion_model as emotion_model
    importlib.reload(emotion_model)
    yield


def test_preprocess_for_model_replaces_numbers_and_keeps_punctuation():
    text = "Привет! Сегодня 123 задачи выполнены."
    result = preprocess_for_model(text)
    assert "<NUM>" in result
    assert result.startswith("привет!")
    assert "задачи" in result
    assert result.endswith("выполнены.")


def test_postprocess_sentiment_scores_normalizes_and_smooths():
    raw_scores = {"positive": 0.1, "neutral": 0.7, "negative": 0.2}
    processed = postprocess_sentiment_scores(raw_scores)
    assert pytest.approx(sum(processed.values()), rel=1e-6) == 1.0
    assert all(0.05 <= v <= 0.95 for v in processed.values())
    assert processed["negative"] < 0.7


def test_calculate_burnout_multifactor_returns_expected_structure(monkeypatch):
    from backend.model.emotion_model import calculate_burnout_multifactor

    text = "Я чувствую усталость и выжат как лимон после рабочего дня."
    scores = {"positive": 0.2, "negative": 0.7}
    history = [
        {"burnout_index": 0.4},
        {"burnout_index": 0.55},
    ]

    result = calculate_burnout_multifactor(text, scores, user_history=history)
    assert isinstance(result, dict)
    assert "burnout_index" in result
    assert "risk_level" in result
    assert result["burnout_index"] >= 0.0
    assert result["burnout_index"] <= 1.0
    assert result["risk_level"] in {"minimal", "low", "medium", "high", "critical"}


def test_extract_keywords_filters_stopwords():
    from backend.utils.keywords import extract_keywords

    text = "Я устал от этой работы, ничего не хочется делать и нет сил."
    keywords = extract_keywords(text)
    assert "работы" in keywords or "устал" in keywords
    assert "я" not in keywords
    assert "не" not in keywords
    assert len(keywords) <= 3
