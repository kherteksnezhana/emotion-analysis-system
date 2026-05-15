"""
Модуль анализа эмоций на основе RuBERT + контекстная постобработка.
Модель: MonoHime/rubert-base-cased-sentiment-new
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
    # Новые константы для контекстной коррекции
    POSITIVE_SUCCESS_MARKERS,
    NEGATIVE_CONTEXT_MARKERS,
    CONTEXT_BOOST_POSITIVE,
    CONTEXT_BOOST_NEGATIVE,
)
from backend.model.text_preprocessor import preprocess_for_model

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- 
# Загрузка модели
# ---------------------------------------------------------------------------
logger.info("Загрузка модели %s...", EMOTION_MODEL_NAME)
print(f"Загрузка модели {EMOTION_MODEL_NAME}...")

classifier = pipeline(
    "sentiment-analysis",
    model=EMOTION_MODEL_NAME,
    device=EMOTION_MODEL_DEVICE,
    top_k=None,
)

print("Модель успешно загружена.")

# --------------------------------------------------------------------------- 
# Маппинги
# ---------------------------------------------------------------------------
_LABEL_MAP: dict[str, str] = {
    "positive": "positive",
    "neutral":  "neutral",
    "negative": "negative",
    "POSITIVE": "positive",
    "NEUTRAL":  "neutral",
    "NEGATIVE": "negative",
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
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _parse_scores(raw_output) -> dict:
    """Парсит выход модели RuBERT"""
    scores = {
        "positive": 0.0,
        "neutral": 0.0,
        "negative": 0.0,
    }

    try:
        # Обработка разных форматов вывода
        if isinstance(raw_output, list) and len(raw_output) > 0 and isinstance(raw_output[0], list):
            items = raw_output[0]
        else:
            items = raw_output

        for item in items:
            raw_label = str(item.get("label", "")).lower()
            label = _LABEL_MAP.get(raw_label, raw_label)
            score = float(item.get("score", 0.0))

            if "positive" in label:
                scores["positive"] = score
            elif "neutral" in label:
                scores["neutral"] = score
            elif "negative" in label:
                scores["negative"] = score

        # Нормализация
        total = sum(scores.values())
        if total > 0:
            scores = {k: round(v / total, 4) for k, v in scores.items()}

    except Exception as e:
        logger.warning(f"Ошибка парсинга scores: {e}")

    return scores


def _detect_markers(text: str, markers_dict: dict) -> float:
    """Определяет силу присутствия маркеров успеха/негатива"""
    if not text:
        return 0.0
    
    text_lower = text.lower()
    score = 0.0

    for level, keywords in markers_dict.items():
        weight = 1.0 if level == "strong" else 0.65
        for kw in keywords:
            count = text_lower.count(kw)
            if count > 0:
                score += weight * min(1.0, count * 0.75)
    
    return min(1.0, score * 0.85)


def _apply_context_correction(scores: dict, text: str) -> tuple[dict, dict]:
    """
    Контекстная коррекция результата модели
    """
    original_pos = scores.get("positive", 0.0)
    original_neg = scores.get("negative", 0.0)

    pos_boost = _detect_markers(text, POSITIVE_SUCCESS_MARKERS)
    neg_boost = _detect_markers(text, NEGATIVE_CONTEXT_MARKERS)

    corrected = scores.copy()

    if pos_boost > 0.1:
        corrected["positive"] = min(1.0, original_pos + pos_boost * CONTEXT_BOOST_POSITIVE)
    
    if neg_boost > 0.1:
        corrected["negative"] = min(1.0, original_neg + neg_boost * CONTEXT_BOOST_NEGATIVE)

    # Нормализация после коррекции
    total = sum(corrected.values())
    if total > 0:
        corrected = {k: round(v / total, 4) for k, v in corrected.items()}

    correction_info = {
        "pos_boost": round(pos_boost, 3),
        "neg_boost": round(neg_boost, 3),
        "was_corrected": pos_boost > 0.1 or neg_boost > 0.1
    }

    return corrected, correction_info


def _detect_burnout_keywords(text: str) -> float:
    """Семантический компонент выгорания"""
    if not text:
        return 0.0
    
    text_lower = text.lower()
    total_score = 0.0

    weight_map = {
        "high": BURNOUT_WEIGHT_HIGH,
        "medium": BURNOUT_WEIGHT_MEDIUM,
        "low": BURNOUT_WEIGHT_LOW,
    }

    for level, keywords in BURNOUT_KEYWORDS.items():
        weight = weight_map.get(level, 0.0)
        for kw in keywords:
            count = text_lower.count(kw)
            if count > 0:
                total_score += weight * min(1.0, count * 0.7)

    semantic = min(1.0, total_score * 0.85)
    return round(semantic, 4)


def _calculate_burnout(
    scores: dict[str, float],
    text: str,
    user_history: Optional[list[dict]],
) -> dict:
    """Расчёт индекса выгорания"""
    positive = scores.get("positive", 0.0)
    negative = scores.get("negative", 0.0)

    emotional = round(negative * 0.75 + (1.0 - positive) * 0.25, 4)
    semantic = _detect_burnout_keywords(text)
    historical = _historical_burnout(user_history)

    burnout_index = round(
        min(
            max(
                emotional * BURNOUT_FACTOR_EMOTIONAL +
                semantic * BURNOUT_FACTOR_SEMANTIC +
                historical * BURNOUT_FACTOR_HISTORICAL,
                0.0
            ),
            1.0
        ),
        4
    )

    risk_level = _burnout_risk_level(burnout_index)
    return {"burnout_index": burnout_index, "risk_level": risk_level}


def _historical_burnout(user_history: Optional[list[dict]]) -> float:
    if not user_history:
        return 0.0

    values = [r["burnout_index"] for r in user_history if r.get("burnout_index") is not None]
    return round(sum(values) / len(values), 4) if values else 0.0


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
        "label": "neutral",
        "display_label": "Нейтральное состояние",
        "score": 0.50,
        "all_scores": {"positive": 0.33, "neutral": 0.40, "negative": 0.27},
        "burnout_index": 0.35,
        "burnout_risk": "medium",
    }


# --------------------------------------------------------------------------- 
# Основная функция
# ---------------------------------------------------------------------------

def analyze_emotion(text: str, user_history: Optional[list[dict]] = None) -> dict:
    """
    Главная функция анализа эмоций с контекстной коррекцией.
    """
    if not text or len(text.strip()) < 15:
        return _default_neutral()

    try:
        cleaned_text = preprocess_for_model(text)
        raw_output = classifier(text[:EMOTION_MODEL_MAX_LENGTH])
        
        scores = _parse_scores(raw_output)
        
        # Применяем контекстную коррекцию
        scores, correction = _apply_context_correction(scores, cleaned_text)

        top_label = max(scores, key=scores.get)

        burnout_result = _calculate_burnout(scores, cleaned_text, user_history)

        result = {
            "label": top_label,
            "display_label": _DISPLAY_LABELS.get(top_label, "Нейтральное состояние"),
            "score": scores[top_label],
            "all_scores": scores,
            "burnout_index": burnout_result["burnout_index"],
            "burnout_risk": burnout_result["risk_level"],
            "correction": correction,
        }

        # Логируем значимые коррекции
        if correction["was_corrected"]:
            logger.info(
                f"Контекстная коррекция: +pos={correction['pos_boost']}, "
                f"+neg={correction['neg_boost']} | {text[:70]}..."
            )

        return result

    except Exception as exc:
        logger.error("Ошибка анализа эмоций: %s", exc)
        return _default_neutral()


# --------------------------------------------------------------------------- 
# Тест при прямом запуске
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_texts = [
        "Отличный день! Закрыл крупную сделку.",
        "Сил нет. Постоянные дедлайны выматывают.",
        "Хочу уволиться, все не нравится.",
        "Обычный день. Задачи выполнил.",
        "Прорыв! Перевыполнил план на 30%.",
        "Не могу больше. Всё валится из рук.",
    ]

    for t in test_texts:
        res = analyze_emotion(t)
        print(f"\nТекст: {t[:80]}...")
        print(f"→ {res['display_label']} ({res['score']:.3f}) | "
              f"Выгорание: {res['burnout_index']:.3f} [{res['burnout_risk']}]")