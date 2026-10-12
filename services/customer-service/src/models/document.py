from sqlalchemy import CHAR, Column, Date, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    document_key = Column(CHAR(36), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    document_type_id = Column(Integer, ForeignKey("document_types.id"), nullable=False)
    document_status_id = Column(Integer, ForeignKey("document_statuses.id"), nullable=False)
    document_number = Column(String(50), nullable=False)
    expiration_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
