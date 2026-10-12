from datetime import date, datetime
from uuid import uuid4

from database import Context
from models import (
    Analysis,
    AnalysisType,
    Customer,
    CustomerEvent,
    CustomerStatus,
    Document,
    DocumentPendency,
    DocumentStatus,
    DocumentType,
    PendencyReason,
)


class CustomerRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session
        self._ids = {}

    # ── clientes ───────────────────────────────────────────────────────

    def create(self, customer_data: dict) -> Customer:
        customer = Customer()
        customer.customer_key = str(uuid4())
        customer.customer_status_id = self.domain_id(CustomerStatus, "PENDING_DOCUMENTS")
        customer.document_number = customer_data["document_number"]
        customer.name = customer_data["name"]
        customer.mother_name = customer_data["mother_name"]
        customer.birth_date = date.fromisoformat(customer_data["birth_date"])
        customer.birth_city = customer_data["birth_city"]
        customer.residence_city = customer_data["residence_city"]
        customer.income_cents = customer_data["income_cents"]
        customer.email = customer_data["email"]
        customer.phone = customer_data["phone"]
        self.session.add(customer)
        self.session.flush()

        self.add_event(customer, "PENDING_DOCUMENTS", "Cadastro criado", {"document_number": customer.document_number})
        return customer

    def get_by_key(self, customer_key: str) -> Customer:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_by_key_of_id(self, customer_id: int) -> Customer:
        return self.session.query(Customer).filter(Customer.id == customer_id).first()

    def get_by_document_number(self, document_number: str) -> Customer:
        return self.session.query(Customer).filter(Customer.document_number == document_number).first()

    def get_by_email(self, email: str) -> Customer:
        return self.session.query(Customer).filter(Customer.email == email).first()

    def get_by_phone(self, phone: str) -> Customer:
        return self.session.query(Customer).filter(Customer.phone == phone).first()

    def status_of(self, customer: Customer) -> str:
        return self.enumerator_of(CustomerStatus, customer.customer_status_id)

    def set_status(self, customer: Customer, enumerator: str, reason: str, payload: dict = None) -> None:
        customer.customer_status_id = self.domain_id(CustomerStatus, enumerator)
        self.add_event(customer, enumerator, reason, payload)

    def add_event(self, customer: Customer, enumerator: str, reason: str, payload: dict = None) -> None:
        event = CustomerEvent()
        event.customer_id = customer.id
        event.customer_status_id = self.domain_id(CustomerStatus, enumerator)
        event.reason = reason
        event.payload = payload
        self.session.add(event)

    def add_analysis(self, customer: Customer, analysis_type: str, result: str, payload,
                     document: Document = None) -> None:
        analysis = Analysis()
        analysis.customer_id = customer.id
        analysis.document_id = document.id if document is not None else None
        analysis.analysis_type_id = self.domain_id(AnalysisType, analysis_type)
        analysis.result = result
        analysis.payload = payload
        self.session.add(analysis)

    # ── documentos ─────────────────────────────────────────────────────

    def create_document(self, customer: Customer, document_type: str, document_data: dict) -> Document:
        document = Document()
        document.document_key = str(uuid4())
        document.customer_id = customer.id
        document.document_type_id = self.domain_id(DocumentType, document_type)
        document.document_status_id = self.domain_id(DocumentStatus, "IN_ANALYSIS")
        document.document_number = document_data["document_number"]
        expiration_date = document_data.get("expiration_date")
        document.expiration_date = date.fromisoformat(expiration_date) if expiration_date else None
        self.session.add(document)
        self.session.flush()
        return document

    def get_document_by_key(self, document_key: str) -> Document:
        return self.session.query(Document).filter(Document.document_key == document_key).first()

    def documents_of(self, customer: Customer) -> list:
        return self.session.query(Document).filter(Document.customer_id == customer.id).order_by(Document.id).all()

    def set_document_status(self, document: Document, enumerator: str) -> None:
        document.document_status_id = self.domain_id(DocumentStatus, enumerator)

    def document_status_of(self, document: Document) -> str:
        return self.enumerator_of(DocumentStatus, document.document_status_id)

    def document_type_of(self, document: Document) -> str:
        return self.enumerator_of(DocumentType, document.document_type_id)

    def is_document_type(self, enumerator: str) -> bool:
        return self.domain_id(DocumentType, enumerator) is not None

    def is_pendency_reason(self, enumerator: str) -> bool:
        return self.domain_id(PendencyReason, enumerator) is not None

    def add_pendency(self, document: Document, reason: str, description: str) -> None:
        pendency = DocumentPendency()
        pendency.document_id = document.id
        pendency.pendency_reason_id = self.domain_id(PendencyReason, reason)
        pendency.description = description
        self.session.add(pendency)

    def resolve_pendencies(self, customer: Customer, document_type: str) -> None:
        """Um documento novo aprovado fecha as pendências abertas dos anteriores do mesmo tipo.
        A pendência não é apagada (R4): ganha a data em que foi resolvida."""
        open_pendencies = (
            self.session.query(DocumentPendency)
            .join(Document, DocumentPendency.document_id == Document.id)
            .filter(
                Document.customer_id == customer.id,
                Document.document_type_id == self.domain_id(DocumentType, document_type),
                DocumentPendency.resolved_at.is_(None),
            )
            .all()
        )
        for pendency in open_pendencies:
            pendency.resolved_at = datetime.now()

    def pendencies_of(self, document: Document) -> list:
        return (
            self.session.query(DocumentPendency, PendencyReason.enumerator)
            .join(PendencyReason, DocumentPendency.pendency_reason_id == PendencyReason.id)
            .filter(DocumentPendency.document_id == document.id)
            .order_by(DocumentPendency.id)
            .all()
        )

    def open_pendencies_of(self, customer: Customer) -> list:
        return (
            self.session.query(DocumentPendency, PendencyReason.enumerator, Document)
            .join(PendencyReason, DocumentPendency.pendency_reason_id == PendencyReason.id)
            .join(Document, DocumentPendency.document_id == Document.id)
            .filter(Document.customer_id == customer.id, DocumentPendency.resolved_at.is_(None))
            .order_by(DocumentPendency.id)
            .all()
        )

    def approved_document_types(self, customer: Customer) -> set:
        rows = (
            self.session.query(DocumentType.enumerator)
            .join(Document, Document.document_type_id == DocumentType.id)
            .filter(
                Document.customer_id == customer.id,
                Document.document_status_id == self.domain_id(DocumentStatus, "APPROVED"),
            )
            .all()
        )
        return {enumerator for (enumerator,) in rows}

    # ── tabelas de domínio ─────────────────────────────────────────────

    def domain_id(self, model, enumerator: str) -> int:
        cache_key = (model.__tablename__, enumerator)
        if cache_key not in self._ids:
            self._ids[cache_key] = self.session.query(model.id).filter(model.enumerator == enumerator).scalar()
        return self._ids[cache_key]

    def enumerator_of(self, model, domain_id: int) -> str:
        return self.session.query(model.enumerator).filter(model.id == domain_id).scalar()
