from datetime import date

import requests
from sqlalchemy.exc import IntegrityError

from connectors import BureauConnector
from controllers.base_controller import BaseController
from errors import (
    DocumentNotFoundInBureau,
    DuplicatedDocumentNumber,
    DuplicatedEmail,
    BureauDataMismatch,
    BureauUnavailable,
    DuplicatedPhone,
    InvalidDocumentNumber,
    CustomerNotFound,
    IrregularDocumentInBureau,
    UnderageCustomer,
)
from dtos import customer_to_dict
from repositories import CustomerRepository
from utils.document_number import is_valid_cpf

MINIMUM_AGE = 15


class CustomerController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)
        self.bureau_connector = BureauConnector()

    def create(self, customer_data: dict) -> dict:
        document_number = customer_data["document_number"]

        if not is_valid_cpf(document_number):
            raise InvalidDocumentNumber(document_number)

        age = self._age_in_years(date.fromisoformat(customer_data["birth_date"]))
        if age < MINIMUM_AGE:
            raise UnderageCustomer(age, MINIMUM_AGE)

        self._check_duplicates(customer_data)

        try:
            bureau_response = self.bureau_connector.consult(document_number)
        except requests.RequestException:
            raise BureauUnavailable()
        if bureau_response.status == 404:
            raise DocumentNotFoundInBureau(document_number)
        bureau_data = bureau_response.json
        if bureau_response.status != 200 or not isinstance(bureau_data, dict) or "document_status" not in bureau_data:
            raise BureauUnavailable()
        if bureau_data["document_status"] != "REGULAR":
            raise IrregularDocumentInBureau(document_number)
        if bureau_data.get("name") != customer_data["name"] or bureau_data.get("birth_date") != customer_data["birth_date"]:
            raise BureauDataMismatch(document_number)

        customer = self.customer_repository.create(customer_data=customer_data)
        try:
            self.session.commit()
        except IntegrityError:
            # Dois cadastros iguais ao mesmo tempo: os dois passaram pela
            # conferência acima, e o UNIQUE barrou o segundo. Conferir de
            # novo diz qual campo repetiu.
            self.session.rollback()
            self._check_duplicates(customer_data)
            raise

        return {"customer_key": customer.customer_key}

    def _check_duplicates(self, customer_data: dict) -> None:
        if self.customer_repository.get_by_document_number(customer_data["document_number"]) is not None:
            raise DuplicatedDocumentNumber(customer_data["document_number"])
        if self.customer_repository.get_by_email(customer_data["email"]) is not None:
            raise DuplicatedEmail(customer_data["email"])
        if self.customer_repository.get_by_phone(customer_data["phone"]) is not None:
            raise DuplicatedPhone(customer_data["phone"])

    def get(self, customer_key: str) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if customer is None:
            raise CustomerNotFound(customer_key)

        return customer_to_dict(customer)

    @staticmethod
    def _age_in_years(birthdate: date) -> int:
        today = date.today()
        had_birthday = (today.month, today.day) >= (birthdate.month, birthdate.day)
        return today.year - birthdate.year - (0 if had_birthday else 1)
