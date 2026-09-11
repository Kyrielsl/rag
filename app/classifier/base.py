from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    domains: list[str]
    confidence: float
    reason: str
    raw_output: str = ""


class Classifier(ABC):
    model: str = ""
    model_version: str = "0.1.0"
    prompt_version: str = "0.1.0"

    @abstractmethod
    def classify(self, content: str, available_domains: list[str]) -> ClassificationResult:
        """把内容分类到可用域，返回域集合与置信度。"""