from datetime import date

import requests

from connectors import DocumentAnalysisConnector
from controllers.base_controller import BaseController
from errors import CustomerNotFound, DocumentAnalysisUnavailable, DocumentNotFound, ExpiredDocument, InvalidDocumentType
from dtos import document_to_dict, document_to_internal_dict
from repositories import CustomerRepository

IDENTITY_DOCUMENTS = {"RG", "CNH"}
ANALYSIS_RESULTS = {"APPROVED", "PENDING", "REJECTED"}


class DocumentController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)
        self.analysis_connector = DocumentAnalysisConnector()

    def create(self, customer_key: str, document_data: dict) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if customer is None:
            raise CustomerNotFound(customer_key)

        document_type = document_data["document_type"]
        if not self.customer_repository.is_document_type(document_type):
            raise InvalidDocumentType(document_type)

        # Documento vencido nem vai para a análise.
        expiration_date = document_data.get("expiration_date")
        if expiration_date is not None and date.fromisoformat(expiration_date) < date.today():
            raise ExpiredDocument(expiration_date)

        document = self.customer_repository.create_document(customer, document_type, document_data)
        analysis = self._analyze(document_type, document_data["document_number"], customer.document_number)

        # O cliente que ainda junta documentos passa por IN_ANALYSIS a cada
        # envio (é o diagrama de estados da RFC); quem já foi aprovado ou
        # rejeitado não muda de estado por mandar outro documento.
        in_onboarding = self.customer_repository.status_of(customer) == "PENDING_DOCUMENTS"
        payload = {"document_key": document.document_key, "document_type": document_type}
        if in_onboarding:
            self.customer_repository.set_status(customer, "IN_ANALYSIS", "Documento enviado para a análise", payload)

        result = analysis["result"]
        self.customer_repository.add_analysis(customer, "DOCUMENT", result, analysis, document=document)
        self.customer_repository.set_document_status(document, result)

        if result == "APPROVED":
            self.customer_repository.resolve_pendencies(customer, document_type)
            self.session.flush()
            if in_onboarding and not self._approve_customer_if_complete(customer):
                self.customer_repository.set_status(customer, "PENDING_DOCUMENTS",
                                                    "Faltam documentos obrigatórios", payload)
        elif result == "PENDING":
            reason = analysis.get("pendency_reason") or "ILLEGIBLE"
            self.customer_repository.add_pendency(document, reason, analysis.get("description"))
            if in_onboarding:
                self.customer_repository.set_status(customer, "PENDING_DOCUMENTS", "Pendência no documento",
                                                    {**payload, "pendency_reason": reason})
        elif self.customer_repository.status_of(customer) != "REJECTED":
            self.customer_repository.set_status(customer, "REJECTED", "Documento reprovado na análise", payload)

        self.session.commit()

        return document_to_dict(document, document_type, result, self.customer_repository.pendencies_of(document))

    def list(self, customer_key: str) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if customer is None:
            raise CustomerNotFound(customer_key)

        # A lista mostra as pendências abertas; as resolvidas continuam no
        # banco, com resolved_at (R4), mas já não pedem nada ao cliente.
        documents = [
            document_to_dict(
                document,
                self.customer_repository.document_type_of(document),
                self.customer_repository.document_status_of(document),
                [(pendency, reason) for pendency, reason in self.customer_repository.pendencies_of(document)
                 if pendency.resolved_at is None],
            )
            for document in self.customer_repository.documents_of(customer)
        ]
        return {"data": documents}

    def get_internal(self, document_key: str) -> dict:
        document = self.customer_repository.get_document_by_key(document_key)
        if document is None:
            raise DocumentNotFound(document_key)

        owner = self.customer_repository.get_by_key_of_id(document.customer_id)
        return document_to_internal_dict(
            document,
            self.customer_repository.document_type_of(document),
            self.customer_repository.document_status_of(document),
            owner.customer_key,
        )

    def _analyze(self, document_type: str, document_number: str, owner_document_number: str) -> dict:
        try:
            response = self.analysis_connector.analyze(document_type, document_number, owner_document_number)
        except requests.RequestException:
            raise DocumentAnalysisUnavailable()

        analysis = response.json
        if response.status != 200 or not isinstance(analysis, dict) or analysis.get("result") not in ANALYSIS_RESULTS:
            raise DocumentAnalysisUnavailable()
        if analysis["result"] == "PENDING" and not self.customer_repository.is_pendency_reason(
                analysis.get("pendency_reason") or "ILLEGIBLE"):
            raise DocumentAnalysisUnavailable()
        return analysis

    def _approve_customer_if_complete(self, customer) -> bool:
        """Um documento de identidade (RG ou CNH) e um comprovante de residência aprovados."""
        approved = self.customer_repository.approved_document_types(customer)
        if not (approved & IDENTITY_DOCUMENTS and "PROOF_OF_ADDRESS" in approved):
            return False

        self.customer_repository.set_status(customer, "APPROVED", "Documentos obrigatórios aprovados",
                                            {"approved_documents": sorted(approved)})
        return True
