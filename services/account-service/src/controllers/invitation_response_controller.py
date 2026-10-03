from datetime import datetime

from controllers.base_controller import BaseController
from errors import HolderNotFound, HolderNotPending
from repositories import AccountRepository


class InvitationResponseController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def accept(self, holder_key: str, customer_key: str) -> dict:
        holder = self._find_pending_holder(holder_key, customer_key)

        holder.status_id = self.account_repository.status_id_of("holder", "ACTIVE")
        holder.joined_at = datetime.now()

        account = self.account_repository.get_account_of(holder)
        if self.account_repository.is_account_in_status(account, "PENDING"):
            account.status_id = self.account_repository.status_id_of("account", "ACTIVE")

        self.session.commit()

        return {"holder_key": holder.holder_key}

    def decline(self, holder_key: str, customer_key: str) -> dict:
        holder = self._find_pending_holder(holder_key, customer_key)

        holder.status_id = self.account_repository.status_id_of("holder", "DECLINED")
        self.session.flush()

        account = self.account_repository.get_account_of(holder)
        if self.account_repository.is_account_in_status(account, "PENDING") and not self.account_repository.has_invited_holders(account):
            self.account_repository.cancel_account(account)

        self.session.commit()

        return {"holder_key": holder.holder_key}

    def _find_pending_holder(self, holder_key: str, customer_key: str):
        holder = self.account_repository.get_holder_for_customer(holder_key, customer_key)
        if holder is None:
            raise HolderNotFound(holder_key)
        if not self.account_repository.is_holder_in_status(holder, "INVITED"):
            raise HolderNotPending(holder_key)

        return holder
