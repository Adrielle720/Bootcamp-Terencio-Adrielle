from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class CustomerEvent(Base):
    __tablename__ = "customer_events"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer_status_id = Column(Integer, ForeignKey("customer_statuses.id"), nullable=False)
    reason = Column(String(255), nullable=True)
    payload = Column(JSONB, nullable=True)
    event_at = Column(DateTime, nullable=False, server_default=func.now())
