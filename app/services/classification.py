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
from app.services.audit import write_audit
from app.services.customer_rules import fields_hit, filename_hit

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


def _run_rules(db: Session, document: Document, content: ExtractedContent | None) -> ClassificationRun | None:
    hit = filename_hit(document.name) or fields_hit(content.fields if content else None)
    if not hit:
        return None

    customer = db.scalar(select(Domain).where(Domain.name == "客户"))
    if customer is None:
        return None

    for old in db.scalars(select(DocumentDomain).where(DocumentDomain.document_id == document.id)).all():
        db.delete(old)

    db.add(
        DocumentDomain(
            document_id=document.id,
            domain_id=customer.id,
            confidence=1.0,
            source="rule",
            reviewed=document.type == "txt",
        )
    )
    document.domain_id = customer.id
    document.sensitive = True
    document.needs_review = document.type == "txt"

    input_text = _build_input(document, content)
    run = ClassificationRun(
        document_id=document.id,
        model="rules",
        model_version="0.1.0",
        prompt_version="0.1.0",
        input_hash=hashlib.sha256(input_text.encode("utf-8")).hexdigest(),
        raw_output="customer rule matched",
        confidence=1.0,
        latency_ms=0,
        status="success",
    )
    db.add(run)
    write_audit(db, action="classify", subject="system", object_id=document.id, result="success")
    db.commit()
    db.refresh(run)
    return run


def run_classification(db: Session, document: Document) -> ClassificationRun:
    ensure_default_domains(db)
    content = db.scalar(
        select(ExtractedContent).where(ExtractedContent.document_id == document.id)
    )

    rule_run = _run_rules(db, document, content)
    if rule_run is not None:
        return rule_run

    available = [d.name for d in db.scalars(select(Domain).where(Domain.enabled == True)).all()]
    if "通用" not in available:
        available.append("通用")

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
    write_audit(db, action="classify", subject="system", object_id=document.id, result=run.status)
    db.commit()
    db.refresh(run)
    return run