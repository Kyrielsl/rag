from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    allowed_domain_ids,
    ensure_search_access,
    get_optional_api_key,
    get_optional_user,
)
from app.db.session import get_db
from app.models.auth import ApiKey, User
from app.models.classification import DocumentDomain
from app.models.document import Document
from app.models.domain import Domain
from app.models.extraction import ExtractedContent
from app.schemas.search import DocumentHit, SearchIn, SearchOut
from app.services.audit import write_audit

router = APIRouter(tags=["search"])


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


def _audit_search(db: Session, body: SearchIn, user: User | None, api_key: ApiKey | None, total: int) -> None:
    write_audit(
        db,
        action="search",
        subject=(user.username if user else api_key.name),
        query_summary=f"q={body.q}, type={body.type}, domain={body.domain}",
        hit_count=total,
        sensitive_hit=body.domain is not None,
    )
    db.commit()


@router.post("/search", response_model=SearchOut)
def search(
    body: SearchIn,
    user: User | None = Depends(get_optional_user),
    api_key: ApiKey | None = Depends(get_optional_api_key),
    db: Session = Depends(get_db),
) -> SearchOut:
    if user is None and api_key is None:
        raise HTTPException(status_code=401, detail="authentication required")
    ensure_search_access(user, api_key)

    allowed = allowed_domain_ids(db, user, api_key)
    if not allowed:
        _audit_search(db, body, user, api_key, 0)
        return SearchOut(items=[], total=0, page=body.page, limit=body.limit)

    filters = []
    if body.name:
        filters.append(Document.name == body.name)
    if body.type:
        filters.append(Document.type == body.type)
    if body.status:
        filters.append(Document.status == body.status)
    else:
        filters.append(Document.status.in_(["CONFIRMED", "READY"]))
    if body.created_from:
        filters.append(Document.created_at >= body.created_from)
    if body.created_to:
        filters.append(Document.created_at <= body.created_to)

    if body.domain:
        domain_ids = [d.id for d in db.scalars(select(Domain).where(Domain.name == body.domain)).all()]
        filters.append(
            Document.id.in_(select(DocumentDomain.document_id).where(DocumentDomain.domain_id.in_(domain_ids)))
        )

    if body.q:
        like = f"%{body.q}%"
        filters.append(
            Document.id.in_(select(ExtractedContent.document_id).where(ExtractedContent.text.ilike(like)))
        )

    forbidden = select(DocumentDomain.document_id).where(DocumentDomain.domain_id.not_in(allowed))
    filters.append(Document.id.not_in(forbidden))

    stmt = select(Document).where(*filters).order_by(Document.created_at.desc())
    total = len(list(db.scalars(stmt).all()))
    items = db.scalars(stmt.offset((body.page - 1) * body.limit).limit(body.limit)).all()

    _audit_search(db, body, user, api_key, total)
    return SearchOut(
        items=[_to_hit(db, d) for d in items],
        total=total,
        page=body.page,
        limit=body.limit,
    )


@router.get("/domains")
def list_domains(
    user: User | None = Depends(get_optional_user),
    api_key: ApiKey | None = Depends(get_optional_api_key),
    db: Session = Depends(get_db),
) -> list[dict]:
    if user is None and api_key is None:
        raise HTTPException(status_code=401, detail="authentication required")
    ensure_search_access(user, api_key)
    allowed = allowed_domain_ids(db, user, api_key)
    return [
        {"id": d.id, "name": d.name, "is_sensitive": d.is_sensitive}
        for d in db.scalars(select(Domain)).all()
        if d.id in allowed
    ]


@router.get("/documents/{document_id}", response_model=DocumentHit)
def get_document(
    document_id: str,
    user: User | None = Depends(get_optional_user),
    api_key: ApiKey | None = Depends(get_optional_api_key),
    db: Session = Depends(get_db),
) -> DocumentHit:
    if user is None and api_key is None:
        raise HTTPException(status_code=401, detail="authentication required")
    ensure_search_access(user, api_key)
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")

    allowed = allowed_domain_ids(db, user, api_key)
    doc_domain_ids = set(
        db.scalars(select(DocumentDomain.domain_id).where(DocumentDomain.document_id == doc.id)).all()
    )
    if not doc_domain_ids.issubset(allowed):
        raise HTTPException(status_code=403, detail="sensitive domain access denied")

    return _to_hit(db, doc)