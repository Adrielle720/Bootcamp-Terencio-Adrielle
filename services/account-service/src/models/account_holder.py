from sqlalchemy import CHAR, BigInteger, Column, Date, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class AccountHolder(Base):
    __tablename__ = "account_holders"

    id = Column(Integer, primary_key=True)
    account_holder_key = Column(CHAR(36), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    customer_key = Column(CHAR(36), nullable=True)
    holder_role_id = Column(Integer, ForeignKey("holder_roles.id"), nullable=False)
    holder_status_id = Column(Integer, ForeignKey("holder_statuses.id"), nullable=False)
    invited_email = Column(String(255), nullable=True)
    invited_phone = Column(String(20), nullable=True)
    name = Column(String(255), nullable=True)
    document_number = Column(CHAR(14), nullable=True)
    birth_date = Column(Date, nullable=True)
    monthly_limit_cents = Column(BigInteger, nullable=True)
    invited_at = Column(DateTime, nullable=False, server_default=func.now())
    joined_at = Column(DateTime, nullable=True)
    left_at = Column(DateTime, nullable=True)
