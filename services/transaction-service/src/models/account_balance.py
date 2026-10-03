from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, func

from models.base import Base


class AccountBalance(Base):
    __tablename__ = "account_balance"
    __table_args__ = (CheckConstraint("balance_cents >= 0"),)

    account_id = Column(Integer, ForeignKey("account.id"), primary_key=True)
    balance_cents = Column(BigInteger, nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())
