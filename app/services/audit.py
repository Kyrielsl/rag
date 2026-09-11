from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit(
    db: Session,
    *,
    action: str,
    subject: str | None = None,
    object_id: str | None = None,
    result: str = "success",
    query_summary: str | None = None,
    hit_count: int = 0,
    sensitive_hit: bool = False,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            subject=subject,
            action=action,
            object_id=object_id,
            result=result,
            query_summary=query_summary,
            hit_count=hit_count,
            sensitive_hit=sensitive_hit,
            ip=ip,
        )
    )