from sqlalchemy import select
from sqlalchemy.orm import Session

from app.extractors.base import ExtractionResult
from app.extractors.registry import get_extractor
from app.models.document import Document
from app.models.extraction import ExtractedContent
from app.storage import get_storage


def run_extraction(db: Session, document: Document) -> ExtractedContent:
    """对单个文档执行内容提取，并把结果写入数据库。"""
    extractor = get_extractor(document.type)
    if extractor is None:
        document.extracted_status = "FAILED"
        document.needs_review = True
        document.parse_summary = {"error": f"unsupported type: {document.type}"}
        db.commit()
        raise ValueError(f"unsupported type: {document.type}")

    data = get_storage().get_object(document.storage_key)
    result: ExtractionResult = extractor.extract(data)

    content = db.scalar(
        select(ExtractedContent).where(ExtractedContent.document_id == document.id)
    )
    if content is None:
        content = ExtractedContent(document_id=document.id)
        db.add(content)

    content.text = result.text
    content.fields = result.fields
    content.rows = result.rows
    content.extractor_version = extractor.version
    content.encoding = result.encoding
    content.delimiter = result.delimiter
    content.warnings = result.warnings

    has_error = any(w.startswith("invalid json") for w in result.warnings)
    if has_error:
        document.extracted_status = "FAILED"
        document.needs_review = True
    else:
        document.extracted_status = "EXTRACTED"
        document.needs_review = bool(result.warnings)

    document.parse_summary = result.summary
    db.commit()
    db.refresh(content)
    return content