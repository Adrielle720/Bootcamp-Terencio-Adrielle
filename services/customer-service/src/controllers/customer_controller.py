from datetime import date

import requests
from sqlalchemy.exc import IntegrityError

from connectors import BureauConnector
from controllers.base_controller import BaseController
from errors import (
    BureauDataMismatch,
    BureauUnavailable,
    CustomerNotFound,
    DocumentNotFoundInBureau,
    DuplicatedDocumentNumber,
    DuplicatedEmail,
    DuplicatedPhone,
    IdempotencyConflict,
    InvalidDocumentNumber,
    IrregularDocumentInBureau,
    UnderageCustomer,
)
from dtos import customer_to_dict, customer_to_internal_dict
from repositories import CustomerRepository, IdempotencyRepository
from utils.document_number import is_valid_cpf
from utils.request_hash import request_hash

MINIMUM_AGE = 15
IDEMPOTENCY_SCOPE = "POST /customers"


class CustomerController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)
        self.idempotency_repository = IdempotencyRepository(self.context)
        self.bureau_connector = BureauConnector()

    def create(self, customer_data: dict, idempotency_key: str = None) -> dict:
        body_hash = request_hash(customer_data)
        previous = self._previous_response(idempotency_key, body_hash)
        if previous is not None:
            return previous

        document_number = customer_data["document_number"]
        if not is_valid_cpf(document_number):
            raise InvalidDocumentNumber(document_number)

        age = self._age_in_years(date.fromisoformat(customer_data["birth_date"]))
        if age < MINIMUM_AGE:
            raise UnderageCustomer(age, MINIMUM_AGE)

        # Duplicidade antes do birô: um CPF já cadastrado não gasta consulta.
        self._check_duplicates(customer_data)

        bureau_data = self._consult_bureau(document_number)

        try:
            customer = self.customer_repository.create(customer_data=customer_data)
            self.customer_repository.add_analysis(customer, "BUREAU_CPF", bureau_data["status"], bureau_data)
            response = {"customer_key": customer.customer_key, "status": "PENDING_DOCUMENTS"}
            if idempotency_key is not None:
                self.idempotency_repository.save(IDEMPOTENCY_SCOPE, idempotency_key, body_hash, 201, response)

            self.session.commit()
        except IntegrityError:
            # Dois pedidos iguais ao mesmo tempo: os dois passaram pela
            # conferência acima, e um UNIQUE barrou o segundo. Conferir de
            # novo diz se foi a mesma chave de idempotência ou o mesmo dado.
            self.session.rollback()
            previous = self._previous_response(idempotency_key, body_hash)
            if previous is not None:
                return previous
            self._check_duplicates(customer_data)
            raise

        return response

    def get(self, customer_key: str) -> dict:
        customer = self._require(customer_key)
        return customer_to_dict(
            customer,
            self.customer_repository.status_of(customer),
            self.customer_repository.open_pendencies_of(customer),
        )

    def get_internal(self, customer_key: str) -> dict:
        customer = self._require(customer_key)
        return customer_to_internal_dict(customer, self.customer_repository.status_of(customer))

    def find_by_contact(self, email: str = None, phone: str = None) -> dict:
        if email is not None:
            customer = self.customer_repository.get_by_email(email)
        else:
            customer = self.customer_repository.get_by_phone(phone)
        if customer is None:
            raise CustomerNotFound(email or phone)

        return customer_to_internal_dict(customer, self.customer_repository.status_of(customer))

    def _consult_bureau(self, document_number: str) -> dict:
        try:
            bureau_response = self.bureau_connector.consult(document_number)
        except requests.RequestException:
            raise BureauUnavailable()

        if bureau_response.status == 404:
            raise DocumentNotFoundInBureau(document_number)

        bureau_data = bureau_response.json
        if bureau_response.status != 200 or not isinstance(bureau_data, dict) or "status" not in bureau_data:
            raise BureauUnavailable()
        if bureau_data["status"] != "REGULAR":
            raise IrregularDocumentInBureau(document_number)
        if not bureau_data.get("name_match") or not bureau_data.get("birth_date_match"):
            raise BureauDataMismatch(document_number)

        return bureau_data

    def _previous_response(self, idempotency_key: str, body_hash: str):
        if idempotency_key is None:
            return None

        record = self.idempotency_repository.get(IDEMPOTENCY_SCOPE, idempotency_key)
        if record is None:
            return None
        if record.request_hash != body_hash:
            raise IdempotencyConflict(idempotency_key)
        return record.response_body

    def _check_duplicates(self, customer_data: dict) -> None:
        if self.customer_repository.get_by_document_number(customer_data["document_number"]) is not None:
            raise DuplicatedDocumentNumber(customer_data["document_number"])
        if self.customer_repository.get_by_email(customer_data["email"]) is not None:
            raise DuplicatedEmail(customer_data["email"])
        if self.customer_repository.get_by_phone(customer_data["phone"]) is not None:
            raise DuplicatedPhone(customer_data["phone"])

    def _require(self, customer_key: str):
        customer = self.customer_repository.get_by_key(customer_key)
        if customer is None:
            raise CustomerNotFound(customer_key)
        return customer

    @staticmethod
    def _age_in_years(birth_date: date) -> int:
        today = date.today()
        had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
        return today.year - birth_date.year - (0 if had_birthday else 1)
