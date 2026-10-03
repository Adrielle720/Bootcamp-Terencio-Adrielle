from controllers.base_controller import BaseController
from errors import CustomerNotFound
from repositories import CustomerRepository


class InvitationListController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.customer_repository = CustomerRepository(self.context)

    def list(self, customer_key: str) -> dict:
        customer = self.customer_repository.get_by_key(customer_key)
        if customer is None:
            raise CustomerNotFound(customer_key)

        invitations = self.customer_repository.list_pending_invitations(customer)

        return {
            "data": [
                {
                    "holder_key": holder.holder_key,
                    "account_key": account.account_key,
                    "account_name": account.name,
                    "invited_at": holder.invited_at.isoformat(),
                }
                for holder, account in invitations
            ]
        }
