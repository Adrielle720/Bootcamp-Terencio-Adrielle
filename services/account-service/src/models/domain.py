from sqlalchemy import Boolean, Column, Integer, String

from models.base import Base


class _DomainTable:
    """Tabela auxiliar de domínio: um valor novo é uma linha nova, sem mudar código."""

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)


class AccountStatus(_DomainTable, Base):
    __tablename__ = "account_statuses"


class HolderRole(_DomainTable, Base):
    __tablename__ = "holder_roles"


class HolderStatus(_DomainTable, Base):
    __tablename__ = "holder_statuses"


class KinshipDegree(_DomainTable, Base):
    __tablename__ = "kinship_degrees"

    requires_custody_order = Column(Boolean, nullable=False)


class GuardianshipStatus(_DomainTable, Base):
    __tablename__ = "guardianship_statuses"


class GuardianshipDocumentPurpose(_DomainTable, Base):
    __tablename__ = "guardianship_document_purposes"


class NotificationType(_DomainTable, Base):
    __tablename__ = "notification_types"
