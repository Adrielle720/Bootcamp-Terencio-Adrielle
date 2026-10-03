from uuid import uuid4

from database import Context
from models import Account, AccountHolder, AccountStatus, Customer, HolderStatus
from utils.account_number import gerar_numero_da_conta


class AccountRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_customer_by_key(self, customer_key: str) -> Customer:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_customer_by_phone(self, phone: str) -> Customer:
        return self.session.query(Customer).filter(Customer.phone == phone).first()

    def create(self, name: str, master: Customer, invited: list) -> Account:
        account = Account()
        account.account_key = str(uuid4())
        account.account_number = gerar_numero_da_conta()
        account.name = name
        account.status_id = self._status_id(AccountStatus, "PENDING")
        self.session.add(account)
        self.session.flush()

        self._add_holder(account, master, "MASTER", "ACTIVE")
        for customer in invited:
            self._add_holder(account, customer, "MEMBER", "INVITED")

        return account

    def _add_holder(self, account: Account, customer: Customer, role: str, status_enumerator: str) -> None:
        holder = AccountHolder()
        holder.holder_key = str(uuid4())
        holder.account_id = account.id
        holder.customer_id = customer.id
        holder.role = role
        holder.status_id = self._status_id(HolderStatus, status_enumerator)
        self.session.add(holder)

    def _status_id(self, model, enumerator: str) -> int:
        return self.session.query(model.id).filter(model.enumerator == enumerator).scalar()
