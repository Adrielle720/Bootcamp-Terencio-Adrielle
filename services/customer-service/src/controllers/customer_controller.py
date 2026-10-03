from datetime import date

from connectors import BureauConnector
from controllers.base_controller import BaseController
from errors import (
    DocumentNotFoundInBureau,
    DuplicatedDocumentNumber,
    DuplicatedEmail,
    DuplicatedPhone,
    InvalidDocumentNumber,
    UnderageCustomer,
)
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

        age = self._age_in_years(date.fromisoformat(customer_data["birthdate"]))
        if age < MINIMUM_AGE:
            raise UnderageCustomer(age, MINIMUM_AGE)

        if self.customer_repository.get_by_document_number(document_number) is not None:
            raise DuplicatedDocumentNumber(document_number)
        if self.customer_repository.get_by_email(customer_data["email"]) is not None:
            raise DuplicatedEmail(customer_data["email"])
        if self.customer_repository.get_by_phone(customer_data["phone"]) is not None:
            raise DuplicatedPhone(customer_data["phone"])

        bureau_response = self.bureau_connector.consult(document_number)
        if bureau_response.status == 404:
            raise DocumentNotFoundInBureau(document_number)

        customer = self.customer_repository.create(customer_data=customer_data)
        self.session.commit()

        return {"customer_key": customer.customer_key}

    @staticmethod
    def _age_in_years(birthdate: date) -> int:
        today = date.today()
        had_birthday = (today.month, today.day) >= (birthdate.month, birthdate.day)
        return today.year - birthdate.year - (0 if had_birthday else 1)
