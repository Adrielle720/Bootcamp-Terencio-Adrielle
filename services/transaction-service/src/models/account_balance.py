from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, func

from models.base import Base


class AccountBalance(Base):
    __tablename__ = "account_balance"

    account_id = Column(Integer, ForeignKey("account.id"), primary_key=True)
    balance_cents = Column(BigInteger, nullable=False)
    allows_negative = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())
