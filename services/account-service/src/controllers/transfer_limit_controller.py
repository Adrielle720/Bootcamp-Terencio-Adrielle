from controllers.base_controller import BaseController
from errors import AccountNotFound, NotMaster
from repositories import AccountRepository


class TransferLimitController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def set(self, account_key: str, customer_key: str, limit_cents) -> dict:
        account = self.account_repository.get_account_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)

        if not self.account_repository.is_master(account, customer_key):
            raise NotMaster(customer_key)

        account.transfer_limit_cents = limit_cents
        self.session.commit()

        return {"account_key": account.account_key, "transfer_limit_cents": limit_cents}
