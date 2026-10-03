from datetime import date

from controllers.base_controller import BaseController
from errors import DuplicatedDocumentNumber, InvalidDocumentNumber, UnderageCustomer
from repositories import CustomerRepository
from utils.document_number import is_valid_cpf

MINIMUM_AGE = 15


class CustomerController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)

    def create(self, customer_data: dict) -> dict:
        if not is_valid_cpf(customer_data["document_number"]):
            raise InvalidDocumentNumber(customer_data["document_number"])

        if self.customer_repository.get_by_document_number(customer_data["document_number"]) is not None:
            raise DuplicatedDocumentNumber(customer_data["document_number"])

        birthdate = date.fromisoformat(customer_data["birthdate"])
        age = self._age_in_years(birthdate)
        if age < MINIMUM_AGE:
            raise UnderageCustomer(age, MINIMUM_AGE)

        customer = self.customer_repository.create(customer_data=customer_data)
        self.session.commit()

        return {"customer_key": customer.customer_key}

    @staticmethod
    def _age_in_years(birthdate: date) -> int:
        today = date.today()
        had_birthday = (today.month, today.day) >= (birthdate.month, birthdate.day)
        return today.year - birthdate.year - (0 if had_birthday else 1)
