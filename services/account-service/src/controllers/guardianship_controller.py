from datetime import datetime

from sqlalchemy.exc import IntegrityError

from connectors import CustomerConnector
from controllers.base_controller import BaseController
from errors import (
    AccountNotFound,
    GuardianNotActiveAdult,
    GuardianshipNotFound,
    HolderIsNotMinorForGuardianship,
    InvalidSchema,
    MinorAlreadyHasGuardian,
    MissingGuardianshipDocument,
)
from repositories import AccountRepository, GuardianshipRepository
from utils.age import is_adult

IDENTITY_DOCUMENTS = {"RG", "CNH"}


class GuardianshipController(BaseController):
    """A guarda é uma relação entre duas pessoas que precisa de prova, não um papel que alguém declara.

    Pais comprovam com a certidão de nascimento do menor; avós e outros
    responsáveis, também com o documento de guarda. Cada documento é
    conferido no customer-service: existe, está aprovado, é do tipo certo
    e é de quem deveria ser.
    """

    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.guardianship_repository = GuardianshipRepository(self.context)
        self.customer_connector = CustomerConnector()

    def create(self, account_key: str, data: dict) -> dict:
        customer_key = data["customer_key"]
        account = self.account_repository.get_account_by_key(account_key)
        guardian = self.account_repository.get_active_holder(account, customer_key)
        if guardian is None:
            raise AccountNotFound(account_key)
        if not is_adult(guardian.birth_date):
            raise GuardianNotActiveAdult(customer_key)

        minor = self.account_repository.get_holder_by_key(data["minor_account_holder_key"])
        if minor is None or minor.account_id != account.id or self.account_repository.holder_role(minor) != "MINOR" \
                or minor.customer_key is None:
            raise HolderIsNotMinorForGuardianship(data["minor_account_holder_key"])
        if self.guardianship_repository.has_approved_guardianship(minor):
            raise MinorAlreadyHasGuardian(minor.account_holder_key)

        kinship = self.guardianship_repository.get_kinship_degree(data["kinship_degree"])
        if kinship is None:
            raise InvalidSchema(f"'{data['kinship_degree']}' is not a valid kinship_degree")

        # Tudo o que vem do customer-service é lido antes de gravar qualquer coisa.
        documents = self._classify_documents(data["document_keys"], guardian, minor)
        required = ["GUARDIAN_ID", "MINOR_BIRTH_CERTIFICATE"]
        if kinship.requires_custody_order:
            required.append("CUSTODY_ORDER")
        for purpose in required:
            if purpose not in documents:
                raise MissingGuardianshipDocument(purpose)

        if kinship.enumerator == "MOTHER":
            minor_customer = self.customer_connector.get_customer(minor.customer_key)
            if minor_customer is None or minor_customer["mother_name"] != guardian.name:
                raise MissingGuardianshipDocument("MINOR_BIRTH_CERTIFICATE com o nome da mãe igual ao da responsável")

        guardianship = self.guardianship_repository.create(minor, guardian, kinship)
        all_approved = all(documents[purpose]["status"] == "APPROVED" for purpose in required)
        for purpose in required:
            self.guardianship_repository.add_document(guardianship, purpose, documents[purpose]["document_key"],
                                                      confirmed=all_approved)

        if all_approved:
            self._approve(guardianship, minor, guardian, account, kinship.enumerator)

        try:
            self.session.commit()
        except IntegrityError:
            # Duas guardas aprovadas ao mesmo tempo para o mesmo menor: o índice único barrou a segunda.
            self.session.rollback()
            raise MinorAlreadyHasGuardian(minor.account_holder_key)

        return self._to_dict(guardianship, minor, guardian)

    def get(self, guardianship_key: str, customer_key: str) -> dict:
        guardianship = self.guardianship_repository.get_by_key(guardianship_key)
        if guardianship is None:
            raise GuardianshipNotFound(guardianship_key)

        minor = self.account_repository.get_holder_by_id(guardianship.minor_account_holder_id)
        guardian = self.account_repository.get_holder_by_id(guardianship.guardian_account_holder_id)
        account = self.account_repository.get_account_by_id(minor.account_id)
        is_party = customer_key in (minor.customer_key, guardian.customer_key)
        if not is_party and self.account_repository.get_active_holder(account, customer_key) is None:
            raise GuardianshipNotFound(guardianship_key)

        return self._to_dict(guardianship, minor, guardian)

    def _classify_documents(self, document_keys: list, guardian, minor) -> dict:
        """Cada documento informado vira a finalidade que ele cumpre, se cumprir alguma.

        Documento inexistente, de outra pessoa ou do tipo errado simplesmente
        não conta: no fim, o que faltar vira 422 QIT002036. Documento
        reprovado também não conta; ainda em análise conta, e deixa a guarda
        em PENDING_DOCUMENTS.
        """
        documents = {}
        for document_key in document_keys:
            document = self.customer_connector.get_document(document_key)
            if document is None or document["status"] == "REJECTED":
                continue

            owner = document["customer_key"]
            if document["document_type"] in IDENTITY_DOCUMENTS and owner == guardian.customer_key:
                purpose = "GUARDIAN_ID"
            elif document["document_type"] == "BIRTH_CERTIFICATE" and owner == minor.customer_key:
                purpose = "MINOR_BIRTH_CERTIFICATE"
            elif document["document_type"] == "CUSTODY_ORDER" and owner in (guardian.customer_key, minor.customer_key):
                purpose = "CUSTODY_ORDER"
            else:
                continue

            if purpose not in documents or document["status"] == "APPROVED":
                documents[purpose] = document
        return documents

    def _approve(self, guardianship, minor, guardian, account, kinship: str) -> None:
        payload = {"kinship_degree": kinship, "guardian": guardian.account_holder_key}
        self.guardianship_repository.set_status(guardianship, "APPROVED", "Documentos confirmados", payload)

        minor.joined_at = datetime.now()
        self.account_repository.set_holder_status(minor, "ACTIVE", "Guarda aprovada", payload)
        # Uma conta só com o master e o menor é válida: o menor ativo ativa a conta pendente.
        if self.account_repository.account_status(account) == "PENDING":
            self.account_repository.set_account_status(account, "ACTIVE", guardian.customer_key,
                                                       "Menor ativado pela guarda aprovada")

        decided = {"guardianship_key": guardianship.guardianship_key, "status": "APPROVED"}
        self.account_repository.notify(guardian.customer_key, account, "GUARDIANSHIP_DECIDED", decided)
        self.account_repository.notify(minor.customer_key, account, "GUARDIANSHIP_DECIDED", decided)

    def _to_dict(self, guardianship, minor, guardian) -> dict:
        return {
            "guardianship_key": guardianship.guardianship_key,
            "status": self.guardianship_repository.status_of(guardianship),
            "kinship_degree": self.guardianship_repository.kinship_of(guardianship),
            "minor_account_holder_key": minor.account_holder_key,
            "guardian_account_holder_key": guardian.account_holder_key,
            "requested_at": guardianship.requested_at.isoformat() if guardianship.requested_at else None,
            "decided_at": guardianship.decided_at.isoformat() if guardianship.decided_at else None,
            "documents": [
                {
                    "purpose": purpose,
                    "document_key": document.document_key,
                    "confirmed_at": document.confirmed_at.isoformat() if document.confirmed_at else None,
                }
                for document, purpose in self.guardianship_repository.documents_of(guardianship)
            ],
        }
