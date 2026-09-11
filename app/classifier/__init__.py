from app.classifier.base import ClassificationResult, Classifier
from app.classifier.deepseek import DeepSeekClassifier

_classifier: Classifier | None = None


def get_classifier() -> Classifier:
    global _classifier
    if _classifier is None:
        _classifier = DeepSeekClassifier()
    return _classifier


__all__ = ["ClassificationResult", "Classifier", "get_classifier"]