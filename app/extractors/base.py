from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    text: str = ""
    fields: dict = field(default_factory=dict)
    rows: list = field(default_factory=list)
    encoding: str | None = None
    delimiter: str | None = None
    warnings: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class Extractor(ABC):
    name: str = "base"
    version: str = "0.1.0"

    @abstractmethod
    def extract(self, data: bytes) -> ExtractionResult:
        """把原始字节解析为统一提取结果。"""