from sqlalchemy import CHAR, BigInteger, Column, Date, DateTime, ForeignKey, Integer, String, func

from models.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    customer_key = Column(CHAR(36), nullable=False)
    customer_status_id = Column(Integer, ForeignKey("customer_statuses.id"), nullable=False)
    document_number = Column(CHAR(14), nullable=False)
    name = Column(String(255), nullable=False)
    mother_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    birth_city = Column(String(255), nullable=False)
    residence_city = Column(String(255), nullable=False)
    income_cents = Column(BigInteger, nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
