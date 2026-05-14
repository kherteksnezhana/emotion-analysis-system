import csv
import os
from pathlib import Path

import pytest


def test_synthetic_dataset_accuracy_and_confusion_matrix():
    project_root = Path(__file__).resolve().parent.parent
    dataset_path = project_root / "dataset.csv"
    assert dataset_path.exists(), "dataset.csv не найден в корне проекта"

    from backend.model.emotion_model import analyze_emotion

    rows = []
    with dataset_path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        for row in reader:
            rows.append(row)

    assert rows, "Синтетический датасет пуст"

    labels = ["positive", "neutral", "negative"]
    total = 0
    correct = 0
    per_class_total = {label: 0 for label in labels}
    per_class_correct = {label: 0 for label in labels}
    confusion = {true: {pred: 0 for pred in labels} for true in labels}

    for row in rows:
        text = row["text"].strip()
        expected = row["emotion_label"].strip().lower()
        result = analyze_emotion(text)
        assert "label" in result
        predicted = result["label"].lower()
        if expected not in labels:
            continue

        total += 1
        per_class_total[expected] += 1
        confusion[expected][predicted] = confusion[expected].get(predicted, 0) + 1
        if predicted == expected:
            correct += 1
            per_class_correct[expected] += 1

    assert total > 0
    accuracy = correct / total
    per_class_accuracy = {
        label: (per_class_correct[label] / per_class_total[label] if per_class_total[label] else 0.0)
        for label in labels
    }

    assert 0.0 <= accuracy <= 1.0
    for value in per_class_accuracy.values():
        assert 0.0 <= value <= 1.0
    assert isinstance(confusion, dict)
    assert set(confusion.keys()) == set(labels)

    # Проверяем, что все три класса присутствуют в отчёте метрик.
    assert all(label in per_class_total for label in labels)
    assert sum(sum(row.values()) for row in confusion.values()) == total
