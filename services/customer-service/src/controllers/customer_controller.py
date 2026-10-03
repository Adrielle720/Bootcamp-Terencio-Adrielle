from controllers.base_controller import BaseController
from errors import InvalidDocumentNumber
from repositories import CustomerRepository
from utils.document_number import is_valid_cpf


class CustomerController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)

    def create(self, customer_data: dict) -> dict:
        if not is_valid_cpf(customer_data["document_number"]):
            raise InvalidDocumentNumber(customer_data["document_number"])

        customer = self.customer_repository.create(customer_data=customer_data)
        self.session.commit()

        return {"customer_key": customer.customer_key}
