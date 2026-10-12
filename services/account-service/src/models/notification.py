from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    notification_key = Column(CHAR(36), nullable=False)
    customer_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    notification_type_id = Column(Integer, ForeignKey("notification_types.id"), nullable=False)
    payload = Column(JSONB, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
