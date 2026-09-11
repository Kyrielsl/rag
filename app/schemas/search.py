from datetime import datetime

from pydantic import BaseModel


class SearchIn(BaseModel):
    q: str | None = None
    name: str | None = None
    type: str | None = None
    domain: str | None = None
    status: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    page: int = 1
    limit: int = 20


class DocumentHit(BaseModel):
    document_id: str
    name: str
    type: str
    status: str
    domains: list[str]
    sensitive: bool
    created_at: datetime


class SearchOut(BaseModel):
    items: list[DocumentHit]
    total: int
    page: int
    limit: int