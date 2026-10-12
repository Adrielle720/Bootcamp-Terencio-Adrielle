from controllers.base_controller import BaseController
from repositories import TransactionRepository


class InstitutionController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.transaction_repository = TransactionRepository(self.context)

    def balances(self) -> dict:
        return self.transaction_repository.institution_balances()
