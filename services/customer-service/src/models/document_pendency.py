from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class DocumentPendency(Base):
    __tablename__ = "document_pendencies"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    pendency_reason_id = Column(Integer, ForeignKey("pendency_reasons.id"), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)
