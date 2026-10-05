from sqlalchemy import CHAR, BigInteger, Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class Transfer(Base):
    __tablename__ = "transfer"

    id = Column(Integer, primary_key=True)
    transaction_key = Column(CHAR(36), nullable=False)
    origin_account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    destination_account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    requested_by_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    verified_holder_id = Column(Integer, ForeignKey("account_holder.id"), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    fee_cents = Column(BigInteger, nullable=False, default=0)
    adult_count = Column(Integer, nullable=False, default=0)
    idempotency_key = Column(String(64), nullable=False)
    request_hash = Column(CHAR(64), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
