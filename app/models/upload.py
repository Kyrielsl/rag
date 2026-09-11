from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.domain import new_uuid, utcnow


class UploadSession(Base):
    __tablename__ = "upload_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id"), index=True)
    upload_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    chunk_size: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="INITIATED")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UploadPart(Base):
    __tablename__ = "upload_part"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("upload_session.id"), index=True)
    part_number: Mapped[int] = mapped_column(Integer)
    etag: Mapped[str] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)