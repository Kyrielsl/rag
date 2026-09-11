from datetime import datetime

from pydantic import BaseModel


class DashboardOut(BaseModel):
    documents: int
    needs_review: int
    domains: int
    api_keys: int


class AuditItem(BaseModel):
    id: str
    subject: str | None
    action: str
    object_id: str | None
    result: str
    query_summary: str | None
    hit_count: int
    sensitive_hit: bool
    ip: str | None
    created_at: datetime


class ReviewIn(BaseModel):
    action: str


class DomainCreateIn(BaseModel):
    name: str
    is_sensitive: bool = False


class DomainUpdateIn(BaseModel):
    enabled: bool | None = None
    is_sensitive: bool | None = None


class ApiKeyListItem(BaseModel):
    id: str
    name: str
    scope: str
    status: str
    expires_at: datetime | None
    created_at: datetime


class ExtractedContentOut(BaseModel):
    text: str
    fields: dict | None
    rows: list | None
    encoding: str | None
    delimiter: str | None
    warnings: list | None


class DomainAssignmentOut(BaseModel):
    domain: str
    confidence: float
    source: str


class AdminDocumentDetail(BaseModel):
    document_id: str
    name: str
    type: str
    size: int
    sha256: str
    status: str
    extracted_status: str
    needs_review: bool
    sensitive: bool
    created_at: datetime
    domains: list[DomainAssignmentOut]
    content: ExtractedContentOut | None