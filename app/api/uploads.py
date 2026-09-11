import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.api.deps import require_upload_access
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.classification import ClassificationRun, DocumentDomain
from app.models.document import Document
from app.models.domain import Domain
from app.models.upload import UploadPart, UploadSession
from app.schemas.uploads import (
    ClassifyOut,
    CompleteIn,
    ConfirmOut,
    ExtractOut,
    InitUploadIn,
    InitUploadOut,
    InstantCheckIn,
    InstantCheckOut,
    PartIn,
    PresignIn,
    PresignOut,
    SessionOut,
)
from app.services.classification import ensure_default_domains, run_classification
from app.services.extraction import run_extraction
from app.storage import get_storage

router = APIRouter(prefix="/uploads", tags=["uploads"], dependencies=[Depends(require_upload_access)])

MULTIPART_THRESHOLD = 10 * 1024 * 1024  # 10MB
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB
TERMINAL_STATUSES = {"UPLOADED", "CONFIRMED", "READY"}
ACTIVE_STATUSES = {"INITIATED", "UPLOADING"}


def _storage_key(document_id: str, name: str) -> str:
    return f"documents/{document_id}/{name}"


def _write_audit(db: Session, action: str, object_id: str | None, result: str = "success") -> None:
    db.add(AuditLog(subject="system", action=action, object_id=object_id, result=result))


def _run_extraction_best_effort(db: Session, doc: Document) -> None:
    try:
        run_extraction(db, doc)
    except Exception as exc:  # noqa: BLE001 - 提取失败不阻塞上传
        db.rollback()
        doc.extracted_status = "FAILED"
        doc.needs_review = True
        doc.parse_summary = {"error": str(exc)}
        db.commit()


def _run_classification_best_effort(db: Session, doc: Document) -> ClassificationRun | None:
    try:
        return run_classification(db, doc)
    except Exception as exc:  # noqa: BLE001 - 分类失败走兜底
        db.rollback()
        ensure_default_domains(db)
        general = db.scalar(select(Domain).where(Domain.name == "通用"))
        if general is not None and doc.domain_id is None:
            doc.domain_id = general.id
        doc.needs_review = True
        db.commit()
        return None


@router.post("/instant", response_model=InstantCheckOut)
def instant_check(body: InstantCheckIn, db: Session = Depends(get_db)) -> InstantCheckOut:
    doc = db.scalar(
        select(Document).where(Document.sha256 == body.sha256, Document.status.in_(TERMINAL_STATUSES))
    )
    return InstantCheckOut(exists=doc is not None, document_id=doc.id if doc else None)


@router.post("/init", response_model=InitUploadOut)
def init_upload(body: InitUploadIn, db: Session = Depends(get_db)) -> InitUploadOut:
    settings = get_settings()
    doc = db.scalar(select(Document).where(Document.sha256 == body.sha256))

    if doc and doc.status in TERMINAL_STATUSES:
        return InitUploadOut(
            session_id="",
            document_id=doc.id,
            chunk_size=0,
            total_chunks=1,
            instant=True,
            existing_document_id=doc.id,
        )

    if doc and doc.status in ACTIVE_STATUSES:
        session = db.scalar(select(UploadSession).where(UploadSession.document_id == doc.id))
        if session:
            return InitUploadOut(
                session_id=session.id,
                document_id=doc.id,
                upload_id=session.upload_id,
                chunk_size=session.chunk_size,
                total_chunks=session.total_chunks,
            )

    if doc is None:
        doc = Document(
            name=body.name,
            type=body.type,
            size=body.size,
            sha256=body.sha256,
            bucket=settings.s3_bucket,
            storage_key="",
            status="INITIATED",
        )
        db.add(doc)
        db.flush()

    doc.name = body.name
    doc.type = body.type
    doc.size = body.size
    doc.storage_key = _storage_key(doc.id, body.name)
    doc.status = "INITIATED"

    is_multipart = body.size > MULTIPART_THRESHOLD
    upload_id: str | None = None
    chunk_size = body.size
    total_chunks = 1

    if is_multipart:
        storage = get_storage()
        upload_id = storage.create_multipart_upload(doc.storage_key)
        chunk_size = CHUNK_SIZE
        total_chunks = math.ceil(body.size / CHUNK_SIZE)

    session = UploadSession(
        document_id=doc.id,
        upload_id=upload_id,
        chunk_size=chunk_size,
        total_chunks=total_chunks,
        status="INITIATED",
    )
    db.add(session)
    _write_audit(db, "upload_init", doc.id)
    db.commit()
    db.refresh(session)

    return InitUploadOut(
        session_id=session.id,
        document_id=doc.id,
        upload_id=upload_id,
        chunk_size=chunk_size,
        total_chunks=total_chunks,
    )


@router.post("/{session_id}/presign", response_model=PresignOut)
def presign_upload(
    session_id: str, body: PresignIn, db: Session = Depends(get_db)
) -> PresignOut:
    session = db.get(UploadSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    doc = db.get(Document, session.document_id)

    storage = get_storage()
    if session.upload_id is not None:
        if body.part_number is None:
            raise HTTPException(status_code=400, detail="part_number is required for multipart upload")
        signed = storage.presign_put(
            doc.storage_key,
            upload_id=session.upload_id,
            part_number=body.part_number,
        )
    else:
        signed = storage.presign_put(doc.storage_key)

    return PresignOut(url=signed.url, method=signed.method)


@router.post("/{session_id}/parts", response_model=PartIn)
def report_part(
    session_id: str, body: PartIn, db: Session = Depends(get_db)
) -> PartIn:
    session = db.get(UploadSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if session.upload_id is None:
        raise HTTPException(status_code=400, detail="not a multipart upload")

    part = db.scalar(
        select(UploadPart).where(
            UploadPart.session_id == session_id,
            UploadPart.part_number == body.part_number,
        )
    )
    if part is None:
        part = UploadPart(
            session_id=session_id,
            part_number=body.part_number,
            etag=body.etag,
            size=body.size,
        )
        db.add(part)
    else:
        part.etag = body.etag
        part.size = body.size

    session.status = "UPLOADING"
    db.commit()
    db.refresh(part)
    return PartIn(part_number=part.part_number, etag=part.etag, size=part.size)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: Session = Depends(get_db)) -> SessionOut:
    session = db.get(UploadSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    parts = db.scalars(
        select(UploadPart.part_number)
        .where(UploadPart.session_id == session_id)
        .order_by(UploadPart.part_number)
    ).all()
    return SessionOut(
        session_id=session.id,
        document_id=session.document_id,
        status=session.status,
        upload_id=session.upload_id,
        chunk_size=session.chunk_size,
        total_chunks=session.total_chunks,
        uploaded_parts=list(parts),
    )


@router.post("/{session_id}/complete", response_model=SessionOut)
def complete_upload(
    session_id: str, body: CompleteIn, db: Session = Depends(get_db)
) -> SessionOut:
    session = db.get(UploadSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if session.upload_id is None:
        raise HTTPException(status_code=400, detail="not a multipart upload")

    doc = db.get(Document, session.document_id)
    parts = [
        {"PartNumber": p.part_number, "ETag": p.etag}
        for p in sorted(body.parts, key=lambda x: x.part_number)
    ]
    get_storage().complete_multipart_upload(doc.storage_key, session.upload_id, parts)

    session.status = "UPLOADED"
    doc.status = "UPLOADED"
    _write_audit(db, "upload_complete", doc.id)
    db.commit()

    return SessionOut(
        session_id=session.id,
        document_id=session.document_id,
        status=session.status,
        upload_id=session.upload_id,
        chunk_size=session.chunk_size,
        total_chunks=session.total_chunks,
        uploaded_parts=[p.part_number for p in body.parts],
    )


@router.post("/{session_id}/confirm", response_model=ConfirmOut)
def confirm_upload(session_id: str, db: Session = Depends(get_db)) -> ConfirmOut:
    session = db.get(UploadSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    doc = db.get(Document, session.document_id)

    storage = get_storage()
    head = storage.head_object(doc.storage_key)
    actual_size = int(head.get("ContentLength", 0))
    if actual_size != doc.size:
        doc.status = "FAILED"
        _write_audit(db, "upload_confirm", doc.id, result="failed")
        db.commit()
        raise HTTPException(status_code=400, detail=f"size mismatch: expected {doc.size}, got {actual_size}")

    doc.status = "CONFIRMED"
    session.status = "CONFIRMED"
    _write_audit(db, "upload_confirm", doc.id)
    db.commit()

    _run_extraction_best_effort(db, doc)
    if doc.extracted_status == "EXTRACTED":
        _run_classification_best_effort(db, doc)

    return ConfirmOut(
        document_id=doc.id,
        status=doc.status,
        extracted_status=doc.extracted_status,
        needs_review=doc.needs_review,
    )


@router.post("/{session_id}/extract", response_model=ExtractOut)
def extract_upload(session_id: str, db: Session = Depends(get_db)) -> ExtractOut:
    session = db.get(UploadSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    doc = db.get(Document, session.document_id)

    _run_extraction_best_effort(db, doc)
    if doc.extracted_status == "EXTRACTED":
        _run_classification_best_effort(db, doc)

    return ExtractOut(
        document_id=doc.id,
        extracted_status=doc.extracted_status,
        needs_review=doc.needs_review,
        summary=doc.parse_summary,
    )


@router.post("/{session_id}/classify", response_model=ClassifyOut)
def classify_upload(session_id: str, db: Session = Depends(get_db)) -> ClassifyOut:
    session = db.get(UploadSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    doc = db.get(Document, session.document_id)

    if doc.extracted_status != "EXTRACTED":
        _run_extraction_best_effort(db, doc)
    run = _run_classification_best_effort(db, doc)

    domain_names = db.scalars(
        select(Domain.name)
        .join(DocumentDomain, DocumentDomain.domain_id == Domain.id)
        .where(DocumentDomain.document_id == doc.id)
    ).all()

    return ClassifyOut(
        document_id=doc.id,
        status=run.status if run is not None else "failed",
        domains=list(domain_names),
        confidence=run.confidence if run is not None else 0.0,
        needs_review=doc.needs_review,
    )


@router.delete("/{session_id}")
def abort_upload(session_id: str, db: Session = Depends(get_db)) -> dict:
    session = db.get(UploadSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    doc = db.get(Document, session.document_id)
    if session.upload_id is not None:
        get_storage().abort_multipart_upload(doc.storage_key, session.upload_id)

    for part in db.scalars(select(UploadPart).where(UploadPart.session_id == session_id)).all():
        db.delete(part)
    db.delete(session)
    doc.status = "FAILED"
    _write_audit(db, "upload_abort", doc.id, result="failed")
    db.commit()
    return {"status": "aborted"}