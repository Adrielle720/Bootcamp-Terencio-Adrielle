from sqlalchemy import CHAR, Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True)
    scope = Column(String(255), nullable=False)
    idempotency_key = Column(String(64), nullable=False)
    request_hash = Column(CHAR(64), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
