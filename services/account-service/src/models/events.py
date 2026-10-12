from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class AccountEvent(Base):
    __tablename__ = "account_events"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    account_status_id = Column(Integer, ForeignKey("account_statuses.id"), nullable=False)
    actor_customer_key = Column(CHAR(36), nullable=True)
    reason = Column(String(255), nullable=True)
    payload = Column(JSONB, nullable=True)
    event_at = Column(DateTime, nullable=False, server_default=func.now())


class AccountHolderEvent(Base):
    __tablename__ = "account_holder_events"

    id = Column(Integer, primary_key=True)
    account_holder_id = Column(Integer, ForeignKey("account_holders.id"), nullable=False)
    holder_status_id = Column(Integer, ForeignKey("holder_statuses.id"), nullable=False)
    holder_role_id = Column(Integer, ForeignKey("holder_roles.id"), nullable=False)
    reason = Column(String(255), nullable=True)
    payload = Column(JSONB, nullable=True)
    event_at = Column(DateTime, nullable=False, server_default=func.now())


class GuardianshipEvent(Base):
    __tablename__ = "guardianship_events"

    id = Column(Integer, primary_key=True)
    guardianship_id = Column(Integer, ForeignKey("guardianships.id"), nullable=False)
    guardianship_status_id = Column(Integer, ForeignKey("guardianship_statuses.id"), nullable=False)
    reason = Column(String(255), nullable=True)
    payload = Column(JSONB, nullable=True)
    event_at = Column(DateTime, nullable=False, server_default=func.now())
