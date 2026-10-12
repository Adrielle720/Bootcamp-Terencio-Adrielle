from sqlalchemy import CHAR, BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class _DomainTable:
    """Tabela auxiliar de domínio: um valor novo é uma linha nova, sem mudar código."""

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)


class BalanceType(_DomainTable, Base):
    __tablename__ = "balance_types"


class EntryType(_DomainTable, Base):
    __tablename__ = "entry_types"


class NotificationType(_DomainTable, Base):
    __tablename__ = "notification_types"


class AccountBalance(Base):
    __tablename__ = "account_balances"

    id = Column(Integer, primary_key=True)
    account_key = Column(CHAR(36), nullable=False)
    balance_type_id = Column(Integer, ForeignKey("balance_types.id"), nullable=False)
    balance_cents = Column(BigInteger, nullable=False)
    allows_negative = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True)
    deposit_key = Column(CHAR(36), nullable=False)
    account_key = Column(CHAR(36), nullable=False)
    depositor_customer_key = Column(CHAR(36), nullable=False)
    depositor_name = Column(String(255), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False)


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True)
    transfer_key = Column(CHAR(36), nullable=False)
    origin_account_key = Column(CHAR(36), nullable=False)
    destination_account_key = Column(CHAR(36), nullable=False)
    requester_customer_key = Column(CHAR(36), nullable=False)
    requester_name = Column(String(255), nullable=False)
    origin_account_number = Column(String(10), nullable=False)
    destination_account_number = Column(String(10), nullable=False)
    verified_holder_name = Column(String(255), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    fee_cents = Column(BigInteger, nullable=False)
    adult_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True)
    account_balance_id = Column(Integer, ForeignKey("account_balances.id"), nullable=False)
    deposit_id = Column(Integer, ForeignKey("deposits.id"), nullable=True)
    transfer_id = Column(Integer, ForeignKey("transfers.id"), nullable=True)
    entry_type_id = Column(Integer, ForeignKey("entry_types.id"), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False)


class FeeTier(Base):
    __tablename__ = "fee_tiers"

    id = Column(Integer, primary_key=True)
    min_amount_cents = Column(BigInteger, nullable=False)
    max_amount_cents = Column(BigInteger, nullable=True)
    base_fee_cents = Column(BigInteger, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    notification_key = Column(CHAR(36), nullable=False)
    customer_key = Column(CHAR(36), nullable=False)
    account_key = Column(CHAR(36), nullable=False)
    notification_type_id = Column(Integer, ForeignKey("notification_types.id"), nullable=False)
    payload = Column(JSONB, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
