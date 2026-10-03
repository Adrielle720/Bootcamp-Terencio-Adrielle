from controllers.base_controller import BaseController
from errors import HolderNotFound, HolderNotPending, NotMaster
from repositories import AccountRepository


class InvitationCancelController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def cancel(self, holder_key: str, customer_key: str) -> dict:
        holder = self.account_repository.get_holder_by_key(holder_key)
        if holder is None:
            raise HolderNotFound(holder_key)

        account = self.account_repository.get_account_of(holder)
        if not self.account_repository.is_master(account, customer_key):
            raise NotMaster(customer_key)

        if not self.account_repository.is_holder_in_status(holder, "INVITED"):
            raise HolderNotPending(holder_key)

        holder.status_id = self.account_repository.status_id_of("holder", "CANCELED")
        self.session.flush()

        if self.account_repository.is_account_in_status(account, "PENDING") and not self.account_repository.has_invited_holders(account):
            self.account_repository.cancel_account(account)

        self.session.commit()

        return {"holder_key": holder.holder_key}
