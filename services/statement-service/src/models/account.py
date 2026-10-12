from sqlalchemy import CHAR, BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True)
    account_key = Column(CHAR(36), nullable=False)
    account_number = Column(String(10), nullable=False)
    name = Column(String(255), nullable=False)
    status_id = Column(Integer, ForeignKey("account_status.id"), nullable=False)
    transfer_limit_cents = Column(BigInteger, nullable=True)
    is_institution = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
