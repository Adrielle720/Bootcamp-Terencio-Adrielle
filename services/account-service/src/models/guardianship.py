from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, func

from models.base import Base


class Guardianship(Base):
    __tablename__ = "guardianships"

    id = Column(Integer, primary_key=True)
    guardianship_key = Column(CHAR(36), nullable=False)
    minor_account_holder_id = Column(Integer, ForeignKey("account_holders.id"), nullable=False)
    guardian_account_holder_id = Column(Integer, ForeignKey("account_holders.id"), nullable=False)
    kinship_degree_id = Column(Integer, ForeignKey("kinship_degrees.id"), nullable=False)
    guardianship_status_id = Column(Integer, ForeignKey("guardianship_statuses.id"), nullable=False)
    requested_at = Column(DateTime, nullable=False, server_default=func.now())
    decided_at = Column(DateTime, nullable=True)


class GuardianshipDocument(Base):
    __tablename__ = "guardianship_documents"

    id = Column(Integer, primary_key=True)
    guardianship_id = Column(Integer, ForeignKey("guardianships.id"), nullable=False)
    guardianship_document_purpose_id = Column(Integer, ForeignKey("guardianship_document_purposes.id"), nullable=False)
    document_key = Column(CHAR(36), nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
