from controllers.base_controller import BaseController
from errors import CustomerNotFound, CustomerNotFoundByPhone
from repositories import AccountRepository


class AccountController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def create(self, account_data: dict) -> dict:
        master = self.account_repository.get_customer_by_key(account_data["customer_key"])
        if master is None:
            raise CustomerNotFound(account_data["customer_key"])

        invited = []
        for phone in account_data["invite_phones"]:
            customer = self.account_repository.get_customer_by_phone(phone)
            if customer is None:
                raise CustomerNotFoundByPhone(phone)
            invited.append(customer)

        account = self.account_repository.create(account_data["name"], master, invited)
        self.session.commit()

        return {"account_key": account.account_key, "account_number": account.account_number}
