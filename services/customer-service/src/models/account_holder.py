from sqlalchemy import CHAR, BigInteger, Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class AccountHolder(Base):
    __tablename__ = "account_holder"

    id = Column(Integer, primary_key=True)
    holder_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    role = Column(String(10), nullable=False)
    status_id = Column(Integer, ForeignKey("holder_status.id"), nullable=False)
    guardian_holder_id = Column(Integer, ForeignKey("account_holder.id"), nullable=True)
    monthly_limit_cents = Column(BigInteger, nullable=True)
    invited_at = Column(DateTime, nullable=False, server_default=func.now())
    joined_at = Column(DateTime, nullable=True)
    left_at = Column(DateTime, nullable=True)
