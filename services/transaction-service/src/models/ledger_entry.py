from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class LedgerEntry(Base):
    __tablename__ = "ledger_entry"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    deposit_id = Column(Integer, ForeignKey("deposit.id"), nullable=True)
    transfer_id = Column(Integer, ForeignKey("transfer.id"), nullable=True)
    entry_type = Column(String(20), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
