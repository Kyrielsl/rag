from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.auth import ApiKey
from app.models.audit import AuditLog
from app.models.classification import DocumentDomain
from app.models.document import Document
from app.models.domain import Domain
from app.models.extraction import ExtractedContent
from app.schemas.console import (
    CustomerFieldsIn,
    AdminDocumentDetail,
    AuditItem,
    DashboardOut,
    DomainAssignmentOut,
    DomainCreateIn,
    DomainUpdateIn,
    ExtractedContentOut,
    ReviewIn,
)
from app.schemas.search import DocumentHit

router = APIRouter(prefix="/admin", tags=["admin-console"], dependencies=[Depends(require_admin)])


def _domain_names(db: Session, document_id: str) -> list[str]:
    return list(
        db.scalars(
            select(Domain.name)
            .join(DocumentDomain, DocumentDomain.domain_id == Domain.id)
            .where(DocumentDomain.document_id == document_id)
        ).all()
    )


def _to_hit(db: Session, doc: Document) -> DocumentHit:
    return DocumentHit(
        document_id=doc.id,
        name=doc.name,
        type=doc.type,
        status=doc.status,
        domains=_domain_names(db, doc.id),
        sensitive=doc.sensitive,
        created_at=doc.created_at,
    )


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    return DashboardOut(
        documents=db.scalar(select(func.count(Document.id))) or 0,
        needs_review=db.scalar(select(func.count(Document.id)).where(Document.needs_review == True)) or 0,
        domains=db.scalar(select(func.count(Domain.id))) or 0,
        api_keys=db.scalar(select(func.count(ApiKey.id))) or 0,
    )


@router.get("/audit", response_model=list[AuditItem])
def list_audit(
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[AuditItem]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = db.scalars(stmt.offset(offset).limit(limit)).all()
    return [AuditItem(**{c.name: getattr(r, c.name) for c in AuditLog.__table__.columns}) for r in rows]


@router.get("/documents", response_model=list[DocumentHit])
def list_documents(
    status: str | None = None,
    needs_review: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[DocumentHit]:
    stmt = select(Document).order_by(Document.created_at.desc())
    if status:
        stmt = stmt.where(Document.status == status)
    if needs_review is not None:
        stmt = stmt.where(Document.needs_review == needs_review)
    docs = db.scalars(stmt.offset(offset).limit(limit)).all()
    return [_to_hit(db, d) for d in docs]


@router.get("/documents/{document_id}", response_model=AdminDocumentDetail)
def get_document_detail(document_id: str, db: Session = Depends(get_db)) -> AdminDocumentDetail:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")

    assignments = db.execute(
        select(Domain.name, DocumentDomain.confidence, DocumentDomain.source)
        .join(DocumentDomain, DocumentDomain.domain_id == Domain.id)
        .where(DocumentDomain.document_id == document_id)
    ).all()

    content = db.scalar(select(ExtractedContent).where(ExtractedContent.document_id == document_id))
    return AdminDocumentDetail(
        document_id=doc.id,
        name=doc.name,
        type=doc.type,
        size=doc.size,
        sha256=doc.sha256,
        status=doc.status,
        extracted_status=doc.extracted_status,
        needs_review=doc.needs_review,
        sensitive=doc.sensitive,
        created_at=doc.created_at,
        domains=[DomainAssignmentOut(domain=n, confidence=c, source=s) for n, c, s in assignments],
        content=(
            ExtractedContentOut(
                text=content.text,
                fields=content.fields,
                rows=content.rows,
                encoding=content.encoding,
                delimiter=content.delimiter,
                warnings=content.warnings,
            )
            if content
            else None
        ),
    )


@router.get("/review-queue", response_model=list[DocumentHit])
def review_queue(db: Session = Depends(get_db)) -> list[DocumentHit]:
    docs = db.scalars(
        select(Document).where(Document.needs_review == True).order_by(Document.created_at.desc())
    ).all()
    return [_to_hit(db, d) for d in docs]


@router.post("/review/{document_id}")
def review_document(document_id: str, body: ReviewIn, db: Session = Depends(get_db)) -> dict:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    if body.action == "approve":
        doc.needs_review = False
        if doc.status not in ("READY",):
            doc.status = "READY"
    elif body.action == "reject":
        doc.needs_review = False
        doc.status = "REJECTED"
    else:
        raise HTTPException(status_code=400, detail="action must be approve or reject")
    db.commit()
    return {"document_id": document_id, "status": doc.status}


@router.post("/domains")
def create_domain(body: DomainCreateIn, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(Domain).where(Domain.name == body.name)):
        raise HTTPException(status_code=409, detail="domain exists")
    domain = Domain(name=body.name, is_sensitive=body.is_sensitive)
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return {"id": domain.id, "name": domain.name, "is_sensitive": domain.is_sensitive}


@router.patch("/domains/{domain_id}")
def update_domain(domain_id: str, body: DomainUpdateIn, db: Session = Depends(get_db)) -> dict:
    domain = db.get(Domain, domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="domain not found")
    if body.enabled is not None:
        domain.enabled = body.enabled
    if body.is_sensitive is not None:
        domain.is_sensitive = body.is_sensitive
    db.commit()
    return {"id": domain.id, "name": domain.name, "enabled": domain.enabled, "is_sensitive": domain.is_sensitive}

@router.patch("/documents/{document_id}/customer-fields")
def save_customer_fields(document_id: str, body: CustomerFieldsIn, db: Session = Depends(get_db)) -> dict:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")

    content = db.scalar(select(ExtractedContent).where(ExtractedContent.document_id == document_id))
    if content is None:
        content = ExtractedContent(document_id=document_id, text="")
        db.add(content)

    normalized: dict = {}
    for key, value in body.fields.items():
        k = str(key)
        if k in ("phone", "email"):
            normalized[k] = value if isinstance(value, list) else [value]
        else:
            normalized[k] = value[0] if isinstance(value, list) and value else value

    merged = dict(content.fields or {})
    merged.update(normalized)
    content.fields = merged

    doc.needs_review = False
    if doc.status not in ("READY",):
        doc.status = "READY"
    db.commit()
    return {"document_id": document_id, "fields": content.fields}