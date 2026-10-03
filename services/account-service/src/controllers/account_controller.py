from datetime import date

from controllers.base_controller import BaseController
from errors import CustomerNotFound, CustomerNotFoundByPhone, MasterIsUnderage
from repositories import AccountRepository


MINIMUM_MASTER_AGE = 18


class AccountController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def create(self, account_data: dict) -> dict:
        master = self.account_repository.get_customer_by_key(account_data["customer_key"])
        if master is None:
            raise CustomerNotFound(account_data["customer_key"])

        age = self._age_in_years(master.birthdate)
        if age < MINIMUM_MASTER_AGE:
            raise MasterIsUnderage(age, MINIMUM_MASTER_AGE)

        invited = []
        for phone in account_data["invite_phones"]:
            customer = self.account_repository.get_customer_by_phone(phone)
            if customer is None:
                raise CustomerNotFoundByPhone(phone)
            invited.append(customer)

        account = self.account_repository.create(account_data["name"], master, invited)
        self.session.commit()

        return {"account_key": account.account_key, "account_number": account.account_number}

    @staticmethod
    def _age_in_years(birthdate: date) -> int:
        today = date.today()
        had_birthday = (today.month, today.day) >= (birthdate.month, birthdate.day)
        return today.year - birthdate.year - (0 if had_birthday else 1)
