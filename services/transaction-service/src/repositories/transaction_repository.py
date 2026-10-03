from uuid import uuid4

from database import Context
from models import Account, AccountBalance, AccountHolder, AccountStatus, Customer, Deposit, HolderStatus, LedgerEntry


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_account_by_key(self, account_key: str) -> Account:
        return self.session.query(Account).filter(Account.account_key == account_key).first()

    def get_customer_by_key(self, customer_key: str) -> Customer:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def is_active_holder(self, account: Account, customer: Customer) -> bool:
        return self.session.query(AccountHolder.id).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.customer_id == customer.id,
            AccountHolder.status_id == self._status_id(HolderStatus, "ACTIVE"),
        ).first() is not None

    def account_status_enumerator(self, account: Account) -> str:
        return self.session.query(AccountStatus.enumerator).filter(AccountStatus.id == account.status_id).scalar()

    def create_deposit(self, account: Account, customer: Customer, amount_cents: int) -> Deposit:
        deposit = Deposit()
        deposit.transaction_key = str(uuid4())
        deposit.account_id = account.id
        deposit.customer_id = customer.id
        deposit.amount_cents = amount_cents
        self.session.add(deposit)
        self.session.flush()

        self.session.add(LedgerEntry(account_id=account.id, deposit_id=deposit.id, entry_type="DEPOSIT", amount_cents=amount_cents))
        self._add_to_balance(account, amount_cents)

        return deposit

    def _add_to_balance(self, account: Account, amount_cents: int) -> None:
        balance = self.session.query(AccountBalance).filter(AccountBalance.account_id == account.id).first()
        if balance is None:
            balance = AccountBalance(account_id=account.id, balance_cents=0)
            self.session.add(balance)
        balance.balance_cents = balance.balance_cents + amount_cents

    def _status_id(self, model, enumerator: str) -> int:
        return self.session.query(model.id).filter(model.enumerator == enumerator).scalar()
