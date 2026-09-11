import csv
import io

from app.extractors.base import Extractor, ExtractionResult
from app.services.customer_rules import FIELD_ALIASES, normalize_fields


class CsvExtractor(Extractor):
    name = "csv"
    version = "0.1.0"

    def extract(self, data: bytes) -> ExtractionResult:
        text, encoding = self._decode(data)
        delimiter = self._detect_delimiter(text)
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)

        warnings: list[str] = []
        rows: list[dict] = []
        header: list[str] = []

        for idx, raw in enumerate(reader):
            if not raw or all(not c.strip() for c in raw):
                continue
            if idx == 0:
                header = self._normalize_header(raw)
                continue
            if len(raw) != len(header):
                warnings.append(f"row {idx} has {len(raw)} columns, expected {len(header)}")
                raw = (raw + [""] * len(header))[: len(header)]
            row = normalize_fields(dict(zip(header, raw)))
            rows.append(row)

        fields = self._collect_fields(rows)

        return ExtractionResult(
            text=text,
            fields=fields,
            rows=rows,
            encoding=encoding,
            delimiter=delimiter,
            warnings=warnings,
            summary={"rows": len(rows), "columns": len(header), "delimiter": delimiter, "customer_hit": bool(fields)},
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
    def _decode(data: bytes) -> tuple[str, str]:
        for enc in ("utf-8", "gbk"):
            try:
                return data.decode(enc), enc
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace"), "utf-8(replace)"

    @staticmethod
    def _detect_delimiter(text: str) -> str:
        sample = next((line for line in text.splitlines() if line.strip()), "")
        candidates = [",", ";", "\t"]
        best = ","
        best_count = -1
        for cand in candidates:
            count = sample.count(cand)
            if count > best_count:
                best_count = count
                best = cand
        return best

    @staticmethod
    def _normalize_header(raw: list[str]) -> list[str]:
        seen: dict[str, int] = {}
        header: list[str] = []
        for col in raw:
            name = col.strip() or "column"
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 1
            header.append(name)
        return header