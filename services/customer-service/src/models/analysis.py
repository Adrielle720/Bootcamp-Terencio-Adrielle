from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    analysis_type_id = Column(Integer, ForeignKey("analysis_types.id"), nullable=False)
    result = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
