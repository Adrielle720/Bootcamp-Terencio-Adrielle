from sqlalchemy import Column, Integer, String

from models.base import Base


class _DomainTable:
    """Tabela auxiliar de domínio: um valor novo é uma linha nova, sem mudar código."""

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)


class CustomerStatus(_DomainTable, Base):
    __tablename__ = "customer_statuses"


class DocumentType(_DomainTable, Base):
    __tablename__ = "document_types"


class DocumentStatus(_DomainTable, Base):
    __tablename__ = "document_statuses"


class PendencyReason(_DomainTable, Base):
    __tablename__ = "pendency_reasons"


class AnalysisType(_DomainTable, Base):
    __tablename__ = "analysis_types"
