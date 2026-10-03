from sqlalchemy import CHAR, BigInteger, Column, DateTime, ForeignKey, Integer, func

from models.base import Base


class Deposit(Base):
    __tablename__ = "deposit"

    id = Column(Integer, primary_key=True)
    transaction_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
