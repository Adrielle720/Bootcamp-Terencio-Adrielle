from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class AccountEvent(Base):
    __tablename__ = "account_event"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("account_status.id"), nullable=False)
    actor_customer_key = Column(CHAR(36), nullable=True)
    reason = Column(String(255), nullable=True)
    event_at = Column(DateTime, nullable=False, server_default=func.now())
