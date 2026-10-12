from sqlalchemy import CHAR, BigInteger, Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    account_key = Column(CHAR(36), nullable=False)
    account_number = Column(String(10), nullable=False)
    account_status_id = Column(Integer, ForeignKey("account_statuses.id"), nullable=False)
    name = Column(String(255), nullable=False)
    transfer_limit_cents = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
