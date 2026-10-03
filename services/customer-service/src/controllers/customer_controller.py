from controllers.base_controller import BaseController
from repositories import CustomerRepository


class CustomerController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)

    def create(self, customer_data: dict) -> dict:
        customer = self.customer_repository.create(customer_data=customer_data)
        self.session.commit()

        return {"customer_key": customer.customer_key}
