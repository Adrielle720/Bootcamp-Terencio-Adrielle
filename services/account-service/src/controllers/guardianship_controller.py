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
        # Só o menor que aceitou e espera a guarda; o que teve a guarda recusada saiu da conta.
        if self.account_repository.holder_status(minor) != "PENDING_GUARDIANSHIP":
            raise HolderIsNotMinorForGuardianship(data["minor_account_holder_key"])

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
        statuses = {purpose: documents[purpose]["status"] for purpose in required}
        all_approved = all(status == "APPROVED" for status in statuses.values())
        for purpose in required:
            self.guardianship_repository.add_document(guardianship, purpose, documents[purpose]["document_key"],
                                                      confirmed=all_approved)

        rejected = sorted(purpose for purpose, status in statuses.items() if status == "REJECTED")
        if rejected:
            self.guardianship_repository.set_status(guardianship, "IN_ANALYSIS", "Documentos enviados para a análise")
            self._reject(guardianship, minor, guardian, account, rejected)
        elif all_approved:
            self.guardianship_repository.set_status(guardianship, "IN_ANALYSIS", "Documentos enviados para a análise")
            self._approve(guardianship, minor, guardian, account, kinship.enumerator)
        # Senão, algum documento ainda está pendente na esteira: a guarda fica
        # PENDING_DOCUMENTS e o menor continua sem movimentar.

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
        não conta: no fim, o que faltar vira 422 QIT002036. Para cada
        finalidade vale o melhor documento informado: aprovado, depois ainda
        em análise (deixa a guarda em PENDING_DOCUMENTS), por último recusado
        (recusa a guarda).
        """
        preference = {"APPROVED": 0, "IN_ANALYSIS": 1, "PENDING": 1, "REJECTED": 2}
        documents = {}
        for document_key in document_keys:
            document = self.customer_connector.get_document(document_key)
            if document is None:
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

            current = documents.get(purpose)
            if current is None or preference[document["status"]] < preference[current["status"]]:
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

        self._notify_decision(guardianship, minor, guardian, account, "APPROVED")

    def _reject(self, guardianship, minor, guardian, account, rejected_purposes: list) -> None:
        """A análise recusou um documento exigido: a guarda é recusada e o
        convite do menor é cancelado, com o motivo no evento."""
        payload = {"rejected_documents": rejected_purposes}
        self.guardianship_repository.set_status(guardianship, "REJECTED", "Documento recusado na análise", payload)
        self.account_repository.set_holder_status(minor, "CANCELED", "Guarda recusada", payload)
        self.account_repository.cancel_if_no_invite_left(account, guardian.customer_key,
                                                         "Guarda do único menor recusada")
        self._notify_decision(guardianship, minor, guardian, account, "REJECTED")

    def _notify_decision(self, guardianship, minor, guardian, account, status: str) -> None:
        decided = {"guardianship_key": guardianship.guardianship_key, "status": status}
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
