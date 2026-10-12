from sqlalchemy import CHAR, BigInteger, Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class Deposit(Base):
    __tablename__ = "deposit"

    id = Column(Integer, primary_key=True)
    deposit_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    idempotency_key = Column(String(64), nullable=True)
    request_hash = Column(CHAR(64), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
