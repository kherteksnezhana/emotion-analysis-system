from transformers import pipeline

classifier = pipeline(
    "sentiment-analysis",
    model="MonoHime/rubert-base-cased-sentiment-new",
    top_k=None,
    device=-1,
)

texts = [
    "Отличный день!",
    "Ненавижу работу",
    "Сегодня обычный день",
]

for t in texts:
    print("\n", t)
    print(classifier(t))