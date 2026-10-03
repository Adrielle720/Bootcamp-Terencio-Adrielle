from controllers.base_controller import BaseController
from errors import AccountNotFound, CustomerNotFoundByPhone, NoSeatsLeft
from repositories import AccountRepository

MAXIMUM_HOLDERS = 6


class InvitationController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def create(self, account_key: str, invitation_data: dict) -> dict:
        account = self.account_repository.get_account_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)

        if self.account_repository.count_open_holders(account) >= MAXIMUM_HOLDERS:
            raise NoSeatsLeft()

        customer = self.account_repository.get_customer_by_phone(invitation_data["phone"])
        if customer is None:
            raise CustomerNotFoundByPhone(invitation_data["phone"])

        holder = self.account_repository.add_invitation(account, customer)
        self.session.commit()

        return {"holder_key": holder.holder_key}
