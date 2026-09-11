import json

from app.extractors.base import Extractor, ExtractionResult
from app.services.customer_rules import FIELD_ALIASES, normalize_fields


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
            flat = normalize_fields(self._flatten(payload))
            fields = self._scalarize({k: [v] for k, v in flat.items() if k in FIELD_ALIASES})
            return ExtractionResult(
                text=text,
                fields=fields,
                encoding=encoding,
                summary={"valid": True, "kind": "object", "customer_hit": bool(fields)},
            )

        if isinstance(payload, list):
            rows = [normalize_fields(self._flatten(item)) for item in payload if isinstance(item, dict)]
            fields = self._collect_fields(rows)
            return ExtractionResult(
                text=text,
                fields=fields,
                rows=rows,
                encoding=encoding,
                summary={"valid": True, "kind": "array", "rows": len(rows), "customer_hit": bool(fields)},
            )

        return ExtractionResult(
            text=text,
            fields={},
            encoding=encoding,
            summary={"valid": True, "kind": "scalar"},
        )

    @staticmethod
    def _collect_fields(rows: list[dict]) -> dict:
        fields: dict = {}
        for canonical in FIELD_ALIASES:
            values = [str(row[canonical]).strip() for row in rows if row.get(canonical)]
            if not values:
                continue
            unique = list(dict.fromkeys(values))
            if canonical in ("phone", "email"):
                fields[canonical] = unique
            else:
                fields[canonical] = ", ".join(unique)
        return fields

    @staticmethod
    def _scalarize(fields: dict) -> dict:
        out: dict = {}
        for key, value in fields.items():
            if key in ("phone", "email"):
                out[key] = value if isinstance(value, list) else [value]
            else:
                out[key] = value[0] if isinstance(value, list) and value else value
        return out

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