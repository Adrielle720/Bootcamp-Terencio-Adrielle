from controllers.base_controller import BaseController
from errors import AccountNotFound, AccountNotPending, NotMaster
from repositories import AccountRepository


class AccountCancelController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def cancel(self, account_key: str, customer_key: str) -> dict:
        account = self.account_repository.get_account_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)

        if not self.account_repository.is_master(account, customer_key):
            raise NotMaster(customer_key)

        if not self.account_repository.is_account_in_status(account, "PENDING"):
            raise AccountNotPending(account_key)

        self.account_repository.cancel_account(account)
        self.session.commit()

        return {"account_key": account.account_key}
