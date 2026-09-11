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