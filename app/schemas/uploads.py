from pydantic import BaseModel


class InstantCheckIn(BaseModel):
    sha256: str
    size: int
    type: str


class InstantCheckOut(BaseModel):
    exists: bool
    document_id: str | None = None


class InitUploadIn(BaseModel):
    name: str
    type: str
    size: int
    sha256: str


class InitUploadOut(BaseModel):
    session_id: str
    document_id: str
    upload_id: str | None = None
    chunk_size: int
    total_chunks: int
    instant: bool = False
    existing_document_id: str | None = None


class PresignIn(BaseModel):
    part_number: int | None = None


class PresignOut(BaseModel):
    url: str
    method: str = "PUT"
    expires_in: int = 900


class PartIn(BaseModel):
    part_number: int
    etag: str
    size: int = 0


class CompleteIn(BaseModel):
    parts: list[PartIn]


class SessionOut(BaseModel):
    session_id: str
    document_id: str
    status: str
    upload_id: str | None = None
    chunk_size: int
    total_chunks: int
    uploaded_parts: list[int]


class ConfirmOut(BaseModel):
    document_id: str
    status: str
    extracted_status: str | None = None
    needs_review: bool | None = None


class ExtractOut(BaseModel):
    document_id: str
    extracted_status: str
    needs_review: bool
    summary: dict | None = None


class ClassifyOut(BaseModel):
    document_id: str
    status: str
    domains: list[str]
    confidence: float
    needs_review: bool