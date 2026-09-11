from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.domain import new_uuid, utcnow


class ExtractedContent(Base):
    __tablename__ = "extracted_content"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id"), index=True, unique=True)
    text: Mapped[str] = mapped_column(Text, default="")
    fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rows: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extractor_version: Mapped[str] = mapped_column(String(64), default="")
    encoding: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delimiter: Mapped[str | None] = mapped_column(String(8), nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)