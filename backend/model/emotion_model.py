"""
Модуль анализа эмоций на основе RuBERT.
Модель: MonoHime/rubert-base-cased-sentiment-new
Метки модели: POSITIVE, NEUTRAL, NEGATIVE
"""
from __future__ import annotations

import logging
from typing import Optional

from transformers import pipeline

from backend.config import (
    BURNOUT_KEYWORDS,
    BURNOUT_WEIGHT_HIGH,
    BURNOUT_WEIGHT_MEDIUM,
    BURNOUT_WEIGHT_LOW,
    BURNOUT_FACTOR_EMOTIONAL,
    BURNOUT_FACTOR_SEMANTIC,
    BURNOUT_FACTOR_HISTORICAL,
    EMOTION_MODEL_NAME,
    EMOTION_MODEL_MAX_LENGTH,
    EMOTION_MODEL_DEVICE,
)
from backend.model.text_preprocessor import preprocess_for_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Маппинг меток модели → внутренние ключи
# Модель MonoHime/rubert-base-cased-sentiment-new возвращает POSITIVE/NEUTRAL/NEGATIVE
# ---------------------------------------------------------------------------
_LABEL_MAP: dict[str, str] = {
    "positive": "positive",
    "neutral":  "neutral",
    "negative": "negative",
    # на случай если модель вернёт верхний регистр
    "POSITIVE": "positive",
    "NEUTRAL":  "neutral",
    "NEGATIVE": "negative",
    # label_0 / label_1 / label_2 — запасной вариант для некоторых чекпоинтов
    "label_0":  "negative",
    "label_1":  "neutral",
    "label_2":  "positive",
}

_DISPLAY_LABELS: dict[str, str] = {
    "positive": "Положительное состояние",
    "neutral":  "Нейтральное состояние",
    "negative": "Негативное состояние",
}

# ---------------------------------------------------------------------------
# Загрузка модели
# ---------------------------------------------------------------------------
logger.info("Загрузка модели %s...", EMOTION_MODEL_NAME)
print(f"Загрузка модели {EMOTION_MODEL_NAME}...")

classifier = pipeline(
    "text-classification",
    model=EMOTION_MODEL_NAME,
    return_all_scores=True,
    device=EMOTION_MODEL_DEVICE,
)

print("Модель загружена.")


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _parse_scores(raw_output) -> dict[str, float]:
    """
    Приводит сырой вывод pipeline к словарю {positive, neutral, negative}.
    Нормализует метки через _LABEL_MAP и обеспечивает наличие всех трёх ключей.
    """
    scores: dict[str, float] = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

    try:
        items = raw_output[0] if isinstance(raw_output[0], list) else raw_output
        for item in items:
            raw_label: str = item.get("label", "")
            score: float = float(item.get("score", 0.0))
            key = _LABEL_MAP.get(raw_label) or _LABEL_MAP.get(raw_label.upper())
            if key:
                scores[key] = round(score, 4)
    except Exception as exc:
        logger.warning("Ошибка разбора вывода модели: %s", exc)

    # Нормализуем на случай, если сумма != 1
    total = sum(scores.values())
    if total > 0:
        scores = {k: round(v / total, 4) for k, v in scores.items()}

    return scores


def _detect_burnout_keywords(text: str) -> float:
    """
    Семантический компонент индекса выгорания.
    Возвращает значение [0.0, 1.0] на основе ключевых слов из конфига.
    """
    text_lower = text.lower()
    max_score = 0.0

    weight_map = {
        "high":   BURNOUT_WEIGHT_HIGH,
        "medium": BURNOUT_WEIGHT_MEDIUM,
        "low":    BURNOUT_WEIGHT_LOW,
    }

    for level, keywords in BURNOUT_KEYWORDS.items():
        weight = weight_map.get(level, 0.0)
        for kw in keywords:
            if kw in text_lower:
                count = text_lower.count(kw)
                score = weight * min(1.0, count / 2.0)
                max_score = max(max_score, score)

    return round(max_score, 4)


def _calculate_burnout(
    scores: dict[str, float],
    text: str,
    user_history: Optional[list[dict]],
) -> dict:
    """
    Многофакторный расчёт индекса выгорания:
      - 60% эмоциональный компонент (из оценок модели)
      - 20% семантический компонент (ключевые слова)
      - 20% исторический компонент (средний burnout из истории)
    """
    positive = scores.get("positive", 0.0)
    negative = scores.get("negative", 0.0)

    # Эмоциональный компонент: чем выше негатив и ниже позитив — тем выше выгорание
    emotional = round(negative * 0.7 + (1.0 - positive) * 0.3, 4)

    # Семантический компонент
    semantic = _detect_burnout_keywords(text)

    # Исторический компонент
    historical = _historical_burnout(user_history)

    burnout_index = round(
        min(
            max(
                emotional * BURNOUT_FACTOR_EMOTIONAL
                + semantic * BURNOUT_FACTOR_SEMANTIC
                + historical * BURNOUT_FACTOR_HISTORICAL,
                0.0,
            ),
            1.0,
        ),
        4,
    )

    risk_level = _burnout_risk_level(burnout_index)
    return {"burnout_index": burnout_index, "risk_level": risk_level}


def _historical_burnout(user_history: Optional[list[dict]]) -> float:
    """Средний индекс выгорания из последних отчётов пользователя."""
    if not user_history:
        return 0.5  # нет истории — нейтральное значение

    values = [
        r["burnout_index"]
        for r in user_history
        if r.get("burnout_index") is not None
    ]
    if not values:
        return 0.5

    return round(sum(values) / len(values), 4)


def _burnout_risk_level(index: float) -> str:
    if index >= 0.7:
        return "critical"
    if index >= 0.5:
        return "high"
    if index >= 0.3:
        return "medium"
    return "low"


def _default_neutral() -> dict:
    return {
        "label":         "neutral",
        "display_label": "Нейтральное состояние",
        "score":         0.50,
        "all_scores":    {"positive": 0.33, "neutral": 0.40, "negative": 0.27},
        "burnout_index": 0.35,
        "burnout_risk":  "medium",
    }


# ---------------------------------------------------------------------------
# Публичный API
# ---------------------------------------------------------------------------

def analyze_emotion(text: str, user_history: Optional[list[dict]] = None) -> dict:
    """
    Анализирует эмоциональное состояние по тексту.

    Args:
        text: текст отчёта сотрудника
        user_history: список предыдущих отчётов (для исторического компонента выгорания)

    Returns:
        Словарь с ключами:
            label         — внутренний ключ (positive / neutral / negative)
            display_label — отображаемое название на русском
            score         — уверенность модели в топ-метке [0, 1]
            all_scores    — словарь вероятностей по всем трём классам
            burnout_index — индекс выгорания [0, 1]
            burnout_risk  — уровень риска (low / medium / high / critical)
    """
    if not text or len(text.strip()) < 15:
        return _default_neutral()

    try:
        cleaned = preprocess_for_model(text)
        raw_output = classifier(cleaned[:EMOTION_MODEL_MAX_LENGTH])
        scores = _parse_scores(raw_output)

        top_label = max(scores, key=scores.get)
        burnout_result = _calculate_burnout(scores, cleaned, user_history)

        return {
            "label":         top_label,
            "display_label": _DISPLAY_LABELS.get(top_label, "Нейтральное состояние"),
            "score":         scores[top_label],
            "all_scores":    scores,
            "burnout_index": burnout_result["burnout_index"],
            "burnout_risk":  burnout_result["risk_level"],
        }

    except Exception as exc:
        logger.error("Ошибка анализа эмоций: %s", exc)
        return _default_neutral()


# ---------------------------------------------------------------------------
# Ручная проверка при запуске напрямую
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    _test_texts = [
        "Месяц закрыт. План 100%.",
        "Усталость накапливается. Сил уже нет.",
        "Отличный день! Закрыл крупную сделку.",
        "Рутина забирает много времени.",
        "Ненавижу эту работу. Хочу уволиться.",
        "Ничего особенного. Сделал текучку, ответил на письма. К вечеру устала, но в целом нормально.",
        "Замечательный день! Закрыл сделку на 1 200 000 ₽.",
    ]
    for t in _test_texts:
        res = analyze_emotion(t)
        print(
            f"\nТекст: {t[:80]}\n"
            f"→ {res['display_label']} ({res['score']:.3f}) | "
            f"Выгорание: {res['burnout_index']:.3f} [{res['burnout_risk']}]"
        )