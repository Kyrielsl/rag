import hashlib
import json
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classifier import get_classifier
from app.models.classification import ClassificationRun, DocumentDomain
from app.models.document import Document
from app.models.domain import Domain
from app.models.extraction import ExtractedContent

DEFAULT_DOMAINS = [("客户", True), ("产品", False), ("合同", True), ("通用", False)]
SINGLE_THRESHOLD = 0.7
MULTI_THRESHOLD = 0.6


def ensure_default_domains(db: Session) -> None:
    existing = {d.name for d in db.scalars(select(Domain)).all()}
    added = False
    for name, sensitive in DEFAULT_DOMAINS:
        if name not in existing:
            db.add(Domain(name=name, is_sensitive=sensitive))
            added = True
    if added:
        db.commit()


def _build_input(document: Document, content: ExtractedContent | None) -> str:
    parts = [f"文件名: {document.name}", f"类型: {document.type}"]
    if content is not None:
        if content.text:
            parts.append(f"内容片段:\n{content.text[:2000]}")
        if content.fields:
            parts.append(f"字段: {json.dumps(content.fields, ensure_ascii=False)[:1000]}")
        if content.rows:
            parts.append(f"行示例: {json.dumps(content.rows[:5], ensure_ascii=False)[:1000]}")
    return "\n".join(parts)


def run_classification(db: Session, document: Document) -> ClassificationRun:
    ensure_default_domains(db)
    available = [d.name for d in db.scalars(select(Domain).where(Domain.enabled == True)).all()]
    if "通用" not in available:
        available.append("通用")

    content = db.scalar(
        select(ExtractedContent).where(ExtractedContent.document_id == document.id)
    )
    input_text = _build_input(document, content)
    input_hash = hashlib.sha256(input_text.encode("utf-8")).hexdigest()

    classifier = get_classifier()
    start = time.monotonic()
    result = classifier.classify(input_text, available)
    latency_ms = int((time.monotonic() - start) * 1000)

    domain_map = {d.name: d for d in db.scalars(select(Domain)).all()}
    domains = [d for d in result.domains if d in domain_map]

    threshold = SINGLE_THRESHOLD if len(domains) == 1 else MULTI_THRESHOLD
    fallback = not domains or result.confidence < threshold

    if fallback:
        domains = ["通用"]
        source = "fallback"
    else:
        source = "model"

    for old in db.scalars(select(DocumentDomain).where(DocumentDomain.document_id == document.id)).all():
        db.delete(old)

    for name in domains:
        dm = domain_map.get(name)
        if dm is None:
            continue
        db.add(
            DocumentDomain(
                document_id=document.id,
                domain_id=dm.id,
                confidence=result.confidence,
                source=source,
                reviewed=fallback,
            )
        )

    primary = domain_map.get(domains[0]) if domains else None
    if primary is not None:
        document.domain_id = primary.id
        document.sensitive = any(domain_map[n].is_sensitive for n in domains if n in domain_map)
    document.needs_review = document.needs_review or fallback

    run = ClassificationRun(
        document_id=document.id,
        model=classifier.model,
        model_version=classifier.model_version,
        prompt_version=classifier.prompt_version,
        input_hash=input_hash,
        raw_output=result.raw_output,
        confidence=result.confidence,
        latency_ms=latency_ms,
        status="fallback" if fallback else "success",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run