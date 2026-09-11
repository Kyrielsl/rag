from app.extractors.base import Extractor, ExtractionResult
from app.services.customer_rules import extract_pii


class TxtExtractor(Extractor):
    name = "txt"
    version = "0.1.0"

    def extract(self, data: bytes) -> ExtractionResult:
        text, encoding = self._decode(data)
        pii = extract_pii(text)
        fields = {k: [v] for k, v in pii.items()}
        lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        return ExtractionResult(
            text=text,
            fields=fields,
            encoding=encoding,
            summary={
                "lines": lines,
                "chars": len(text),
                "customer_hit": bool(pii),
            },
        )

    @staticmethod
    def _decode(data: bytes) -> tuple[str, str]:
        for enc in ("utf-8", "gbk"):
            try:
                return data.decode(enc), enc
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace"), "utf-8(replace)"