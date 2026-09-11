from app.extractors.base import Extractor
from app.extractors.csv import CsvExtractor
from app.extractors.json import JsonExtractor
from app.extractors.txt import TxtExtractor

_REGISTRY: dict[str, Extractor] = {
    "txt": TxtExtractor(),
    "csv": CsvExtractor(),
    "json": JsonExtractor(),
}


def get_extractor(doc_type: str) -> Extractor | None:
    return _REGISTRY.get(doc_type.lower())