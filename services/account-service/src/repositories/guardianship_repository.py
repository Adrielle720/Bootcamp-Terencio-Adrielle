from datetime import datetime
from uuid import uuid4

from database import Context
from models import (
    AccountHolder,
    Guardianship,
    GuardianshipDocument,
    GuardianshipDocumentPurpose,
    GuardianshipEvent,
    GuardianshipStatus,
    KinshipDegree,
)


class GuardianshipRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session
        self._ids = {}

    def get_kinship_degree(self, enumerator: str) -> KinshipDegree:
        return self.session.query(KinshipDegree).filter(KinshipDegree.enumerator == enumerator).first()

    def get_by_key(self, guardianship_key: str) -> Guardianship:
        return self.session.query(Guardianship).filter(Guardianship.guardianship_key == guardianship_key).first()

    def has_approved_guardianship(self, minor: AccountHolder) -> bool:
        return self.session.query(Guardianship.id).filter(
            Guardianship.minor_account_holder_id == minor.id,
            Guardianship.guardianship_status_id == self.domain_id(GuardianshipStatus, "APPROVED"),
        ).first() is not None

    def approved_guardianships_of(self, minor: AccountHolder) -> list:
        return self.session.query(Guardianship).filter(
            Guardianship.minor_account_holder_id == minor.id,
            Guardianship.guardianship_status_id == self.domain_id(GuardianshipStatus, "APPROVED"),
        ).all()

    def create(self, minor: AccountHolder, guardian: AccountHolder, kinship_degree: KinshipDegree) -> Guardianship:
        guardianship = Guardianship()
        guardianship.guardianship_key = str(uuid4())
        guardianship.minor_account_holder_id = minor.id
        guardianship.guardian_account_holder_id = guardian.id
        guardianship.kinship_degree_id = kinship_degree.id
        guardianship.guardianship_status_id = self.domain_id(GuardianshipStatus, "PENDING_DOCUMENTS")
        self.session.add(guardianship)
        self.session.flush()

        self.add_event(guardianship, "Guarda pedida", {"kinship_degree": kinship_degree.enumerator})
        return guardianship

    def add_document(self, guardianship: Guardianship, purpose: str, document_key: str, confirmed: bool) -> None:
        document = GuardianshipDocument()
        document.guardianship_id = guardianship.id
        document.guardianship_document_purpose_id = self.domain_id(GuardianshipDocumentPurpose, purpose)
        document.document_key = document_key
        document.confirmed_at = datetime.now() if confirmed else None
        self.session.add(document)

    def documents_of(self, guardianship: Guardianship) -> list:
        return (
            self.session.query(GuardianshipDocument, GuardianshipDocumentPurpose.enumerator)
            .join(GuardianshipDocumentPurpose,
                  GuardianshipDocument.guardianship_document_purpose_id == GuardianshipDocumentPurpose.id)
            .filter(GuardianshipDocument.guardianship_id == guardianship.id)
            .order_by(GuardianshipDocument.id)
            .all()
        )

    def set_status(self, guardianship: Guardianship, enumerator: str, reason: str, payload: dict = None) -> None:
        guardianship.guardianship_status_id = self.domain_id(GuardianshipStatus, enumerator)
        if enumerator in ("APPROVED", "REJECTED"):
            guardianship.decided_at = datetime.now()
        self.add_event(guardianship, reason, payload)

    def status_of(self, guardianship: Guardianship) -> str:
        return self.session.query(GuardianshipStatus.enumerator).filter(
            GuardianshipStatus.id == guardianship.guardianship_status_id).scalar()

    def kinship_of(self, guardianship: Guardianship) -> str:
        return self.session.query(KinshipDegree.enumerator).filter(
            KinshipDegree.id == guardianship.kinship_degree_id).scalar()

    def add_event(self, guardianship: Guardianship, reason: str, payload: dict = None) -> None:
        event = GuardianshipEvent()
        event.guardianship_id = guardianship.id
        event.guardianship_status_id = guardianship.guardianship_status_id
        event.reason = reason
        event.payload = payload
        self.session.add(event)

    def domain_id(self, model, enumerator: str) -> int:
        cache_key = (model.__tablename__, enumerator)
        if cache_key not in self._ids:
            self._ids[cache_key] = self.session.query(model.id).filter(model.enumerator == enumerator).scalar()
        return self._ids[cache_key]
