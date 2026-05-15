from pprint import pprint

from backend.model.emotion_model import (
    classifier,
    analyze_emotion,
    _parse_scores,
    _detect_burnout_keywords,
    _historical_burnout,
)
from backend.model.text_preprocessor import preprocess_for_model


TEST_TEXTS = [
    "Месяц закрыт. План 100%.",
    "Усталость накапливается. Сил уже нет.",
    "Отличный день! Закрыл крупную сделку.",
    "Рутина забирает много времени.",
    "Ненавижу эту работу. Хочу уволиться.",
    "Ничего особенного. Сделал текучку, ответил на письма.",
    "Замечательный день! Закрыл сделку на 1 200 000 ₽.",
    "Я очень устал и чувствую стресс.",
    "Все отлично :) работал до 3 ночи",
]

# Тестовая история пользователя
USER_HISTORY = [
    {"burnout_index": 0.45},
    {"burnout_index": 0.52},
    {"burnout_index": 0.61},
    {"burnout_index": 0.58},
]


def print_separator():
    print("\n" + "=" * 80 + "\n")


def debug_single_text(text: str):
    print_separator()

    print(f"ORIGINAL TEXT:\n{text}")

    # ------------------------------------------------------------------
    # preprocessing
    # ------------------------------------------------------------------
    cleaned = preprocess_for_model(text)

    print("\nPREPROCESSED:")
    print(cleaned)

    # ------------------------------------------------------------------
    # raw model output
    # ------------------------------------------------------------------
    raw_output = classifier(cleaned)

    print("\nRAW MODEL OUTPUT:")
    pprint(raw_output)

    print("\nTYPE INFO:")
    print("type(raw_output) =", type(raw_output))

    if isinstance(raw_output, list) and len(raw_output) > 0:
        print("type(raw_output[0]) =", type(raw_output[0]))

    # ------------------------------------------------------------------
    # parsed scores
    # ------------------------------------------------------------------
    scores = _parse_scores(raw_output)

    print("\nPARSED SCORES:")
    pprint(scores)

    # ------------------------------------------------------------------
    # softmax check
    # ------------------------------------------------------------------
    total = sum(scores.values())

    print("\nSOFTMAX CHECK:")
    print(f"SUM = {total:.6f}")

    # ------------------------------------------------------------------
    # top label
    # ------------------------------------------------------------------
    top_label = max(scores, key=scores.get)

    print("\nTOP LABEL:")
    print(top_label)
    print(f"CONFIDENCE = {scores[top_label]:.4f}")

    # ------------------------------------------------------------------
    # semantic burnout
    # ------------------------------------------------------------------
    semantic = _detect_burnout_keywords(cleaned)

    print("\nSEMANTIC COMPONENT:")
    print(f"semantic_score = {semantic:.4f}")

    # ------------------------------------------------------------------
    # historical burnout
    # ------------------------------------------------------------------
    historical = _historical_burnout(USER_HISTORY)

    print("\nHISTORICAL COMPONENT:")
    print(f"historical_score = {historical:.4f}")

    # ------------------------------------------------------------------
    # full analysis
    # ------------------------------------------------------------------
    result = analyze_emotion(
        text=text,
        user_history=USER_HISTORY,
    )

    print("\nFINAL ANALYSIS:")
    pprint(result)

    # ------------------------------------------------------------------
    # emotional component explanation
    # ------------------------------------------------------------------
    positive = scores.get("positive", 0.0)
    negative = scores.get("negative", 0.0)

    emotional = round(
        negative * 0.7 + (1.0 - positive) * 0.3,
        4,
    )

    print("\nEMOTIONAL COMPONENT:")
    print(
        f"({negative:.4f} * 0.7) + "
        f"((1 - {positive:.4f}) * 0.3)"
    )

    print(f"emotional_score = {emotional:.4f}")

    print_separator()


if __name__ == "__main__":
    print("\nMODEL DEBUG TEST\n")

    for text in TEST_TEXTS:
        debug_single_text(text)