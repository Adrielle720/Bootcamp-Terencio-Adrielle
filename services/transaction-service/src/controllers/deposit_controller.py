from controllers.base_controller import BaseController
from errors import AccountNotAvailable, AccountNotFound
from repositories import TransactionRepository

DEPOSITABLE_STATUSES = ["ACTIVE", "BLOCKED", "CLOSING"]


class DepositController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.transaction_repository = TransactionRepository(self.context)

    def create(self, account_key: str, deposit_data: dict) -> dict:
        account = self.transaction_repository.get_account_by_key(account_key)
        customer = self.transaction_repository.get_customer_by_key(deposit_data["customer_key"])

        if account is None or customer is None or not self.transaction_repository.is_active_holder(account, customer):
            raise AccountNotFound(account_key)

        if self.transaction_repository.account_status_enumerator(account) not in DEPOSITABLE_STATUSES:
            raise AccountNotAvailable(account_key)

        deposit = self.transaction_repository.create_deposit(account, customer, deposit_data["amount_cents"])
        self.session.commit()

        return {"transaction_key": deposit.transaction_key}
