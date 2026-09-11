import json

from app.extractors.base import Extractor, ExtractionResult


class JsonExtractor(Extractor):
    name = "json"
    version = "0.1.0"

    def extract(self, data: bytes) -> ExtractionResult:
        text, encoding = self._decode(data)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return ExtractionResult(
                text=text,
                encoding=encoding,
                warnings=[f"invalid json: {exc}"],
                summary={"valid": False},
            )

        if isinstance(payload, dict):
            fields = self._flatten(payload)
            return ExtractionResult(
                text=text,
                fields=fields,
                encoding=encoding,
                summary={"valid": True, "kind": "object", "fields": len(fields)},
            )

        if isinstance(payload, list):
            rows = payload if all(isinstance(i, dict) for i in payload) else []
            fields: dict = {}
            if rows:
                fieldset = sorted({k for row in rows for k in row.keys()})
                fields = {k: "" for k in fieldset}
            return ExtractionResult(
                text=text,
                fields=fields,
                rows=rows,
                encoding=encoding,
                summary={"valid": True, "kind": "array", "rows": len(rows)},
            )

        return ExtractionResult(
            text=text,
            fields={"value": payload},
            encoding=encoding,
            summary={"valid": True, "kind": "scalar"},
        )

    @staticmethod
    def _decode(data: bytes) -> tuple[str, str]:
        for enc in ("utf-8", "gbk"):
            try:
                return data.decode(enc), enc
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace"), "utf-8(replace)"

    @staticmethod
    def _flatten(obj: dict, prefix: str = "") -> dict:
        out: dict = {}
        for key, value in obj.items():
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                out.update(JsonExtractor._flatten(value, full))
            else:
                out[full] = value
        return out