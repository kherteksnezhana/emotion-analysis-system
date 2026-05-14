"""
Улучшенная v3 — баланс + чувствительность к контексту
"""
from transformers import pipeline

from backend.config import (
    BURNOUT_KEYWORDS, BURNOUT_WEIGHT_HIGH, BURNOUT_WEIGHT_MEDIUM, BURNOUT_WEIGHT_LOW,
    BURNOUT_FACTOR_EMOTIONAL, BURNOUT_FACTOR_SEMANTIC, BURNOUT_FACTOR_HISTORICAL,
    BURNOUT_RISK_THRESHOLDS, EMOTION_MODEL_NAME, EMOTION_MODEL_MAX_LENGTH,
    EMOTION_MODEL_DEVICE, POSITIVE_KEYWORDS, POSITIVE_PHRASES,
    NEGATIVE_STRONG_PHRASES, NEGATIVE_WEAK_PHRASES
)
from backend.model.text_preprocessor import preprocess_for_model, postprocess_sentiment_scores


print("Загрузка модели RuBERT...")

classifier = pipeline(
    "text-classification",
    model=EMOTION_MODEL_NAME,
    return_all_scores=True,
    device=EMOTION_MODEL_DEVICE,
)


def safe_get_scores(output) -> dict:
    try:
        if isinstance(output, list) and len(output) > 0:
            items = output[0] if isinstance(output[0], list) else output
            scores = {}
            for item in items:
                if isinstance(item, dict) and 'label' in item and 'score' in item:
                    scores[item['label'].lower()] = round(float(item['score']), 4)
            return scores
    except:
        pass
    return {"positive": 0.35, "neutral": 0.40, "negative": 0.25}


def detect_burnout_keywords(text: str) -> float:
    text_lower = text.lower()
    max_score = 0.0
    for level, keywords in BURNOUT_KEYWORDS.items():
        weight = BURNOUT_WEIGHT_HIGH if level == "high" else \
                 BURNOUT_WEIGHT_MEDIUM if level == "medium" else BURNOUT_WEIGHT_LOW
        for kw in keywords:
            if kw in text_lower:
                count = text_lower.count(kw)
                score = weight * min(1.0, count / 2.0)
                max_score = max(max_score, score)
    return round(max_score, 4)


def analyze_emotion(text: str, user_history: list = None) -> dict:
    if not text or len(text.strip()) < 15:
        return default_neutral()

    try:
        cleaned_text = preprocess_for_model(text)
        raw_output = classifier(cleaned_text[:EMOTION_MODEL_MAX_LENGTH])
        scores = safe_get_scores(raw_output)

        scores = postprocess_sentiment_scores(scores)

        text_lower = text.lower()

        # === УЛУЧШЕННАЯ ЛОГИКА v3 ===
        positive_boost = 0.0
        negative_boost = 0.0

        # Сильный позитив (успехи, достижения)
        if any(phrase in text_lower for phrase in POSITIVE_PHRASES):
            positive_boost = 0.32
        elif any(word in text_lower for word in POSITIVE_KEYWORDS):
            positive_boost = 0.20

        # Сильный негатив
        if any(phrase in text_lower for phrase in NEGATIVE_STRONG_PHRASES):
            negative_boost = 0.48
        # Слабый негатив / усталость
        elif any(phrase in text_lower for phrase in NEGATIVE_WEAK_PHRASES):
            # "устала, но нормально" — не должно быть сильным негативом
            if "но в целом" in text_lower or "но нормально" in text_lower or "но всё ок" in text_lower:
                negative_boost = 0.12
            else:
                negative_boost = 0.27

        # Применяем
        if positive_boost > 0:
            scores['positive'] = min(scores.get('positive', 0) + positive_boost, 0.95)
            scores['negative'] = max(scores.get('negative', 0) - 0.22, 0.02)

        if negative_boost > 0:
            scores['negative'] = min(scores.get('negative', 0) + negative_boost, 0.95)
            scores['positive'] = max(scores.get('positive', 0) - 0.23, 0.02)

        # Нормализация
        total = sum(scores.values())
        if total > 0:
            for k in scores:
                scores[k] = round(scores[k] / total, 4)

        top_label = max(scores, key=scores.get)
        label_map = {
            "positive": "Положительное состояние",
            "neutral": "Нейтральное состояние",
            "negative": "Негативное состояние",
        }

        burnout_result = calculate_burnout_multifactor(cleaned_text, scores, user_history)

        return {
            "label": top_label,
            "display_label": label_map.get(top_label, "Нейтральное состояние"),
            "score": round(scores.get(top_label, 0.5), 4),
            "all_scores": scores,
            "burnout_index": burnout_result["burnout_index"],
            "burnout_risk": burnout_result["risk_level"]
        }

    except Exception as e:
        print(f"[ERROR] {e}")
        return default_neutral()


def default_neutral():
    return {
        "label": "neutral",
        "display_label": "Нейтральное состояние",
        "score": 0.50,
        "all_scores": {"positive": 0.33, "neutral": 0.40, "negative": 0.27},
        "burnout_index": 0.35,
        "burnout_risk": "medium"
    }


def calculate_burnout_multifactor(text: str, scores: dict, user_history=None) -> dict:
    positive = scores.get("positive", 0.0)
    negative = scores.get("negative", 0.0)

    emotional = round(negative * 0.7 + (1 - positive) * 0.3, 4)
    semantic = detect_burnout_keywords(text)
    historical = 0.5

    burnout_index = round(min(max(
        emotional * BURNOUT_FACTOR_EMOTIONAL +
        semantic * BURNOUT_FACTOR_SEMANTIC +
        historical * BURNOUT_FACTOR_HISTORICAL, 0.0), 1.0), 4)

    if burnout_index >= 0.7: risk = "critical"
    elif burnout_index >= 0.5: risk = "high"
    elif burnout_index >= 0.3: risk = "medium"
    else: risk = "low"

    return {"burnout_index": burnout_index, "risk_level": risk}


if __name__ == "__main__":
    tests = [
        "Месяц закрыт. План 100%.",
        "Усталость накапливается. Сил уже нет.",
        "Отличный день! Закрыл крупную сделку.",
        "Рутина забирает много времени.",
        "Ненавижу эту работу. Хочу уволиться.",
        "Ничего особенного. Сделал текучку, ответил на письма. К вечеру устала, но в целом нормально.",
        "Замечательный день! Закрыл сделку на 1 200 000 ₽."
    ]
    for t in tests:
        res = analyze_emotion(t)
        print(f"\nТекст: {t[:100]}...")
        print(f"→ {res['display_label']} ({res['score']:.3f}) | Выгорание: {res['burnout_index']:.3f}")