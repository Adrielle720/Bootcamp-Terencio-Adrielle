from uuid import uuid4

from database import Context
from models import (
    Account,
    AccountBalance,
    AccountHolder,
    AccountStatus,
    Customer,
    Deposit,
    HolderStatus,
    LedgerEntry,
    Transfer,
)


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_account_by_key(self, account_key: str) -> Account:
        return self.session.query(Account).filter(Account.account_key == account_key).first()

    def get_account_by_number(self, account_number: str) -> Account:
        return self.session.query(Account).filter(Account.account_number == account_number).first()

    def get_customer_by_key(self, customer_key: str) -> Customer:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_customer_by_document(self, document_number: str) -> Customer:
        return self.session.query(Customer).filter(Customer.document_number == document_number).first()

    def get_active_holder(self, account: Account, customer: Customer) -> AccountHolder:
        return self.session.query(AccountHolder).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.customer_id == customer.id,
            AccountHolder.status_id == self._status_id(HolderStatus, "ACTIVE"),
        ).first()

    def is_active_holder(self, account: Account, customer: Customer) -> bool:
        return self.get_active_holder(account, customer) is not None

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
        self.add_to_balance(account, amount_cents)

        return deposit

    def create_transfer(self, origin: Account, destination: Account, requester: Customer,
                        verified_holder: AccountHolder, amount_cents: int, idempotency_key: str) -> Transfer:
        transfer = Transfer()
        transfer.transaction_key = str(uuid4())
        transfer.origin_account_id = origin.id
        transfer.destination_account_id = destination.id
        transfer.requested_by_id = requester.id
        transfer.verified_holder_id = verified_holder.id
        transfer.amount_cents = amount_cents
        transfer.idempotency_key = idempotency_key
        self.session.add(transfer)
        self.session.flush()

        self.session.add(LedgerEntry(account_id=origin.id, transfer_id=transfer.id, entry_type="TRANSFER_OUT", amount_cents=-amount_cents))
        self.session.add(LedgerEntry(account_id=destination.id, transfer_id=transfer.id, entry_type="TRANSFER_IN", amount_cents=amount_cents))
        self.add_to_balance(origin, -amount_cents)
        self.add_to_balance(destination, amount_cents)

        return transfer

    def add_to_balance(self, account: Account, delta_cents: int) -> None:
        balance = self.session.query(AccountBalance).filter(AccountBalance.account_id == account.id).first()
        if balance is None:
            balance = AccountBalance(account_id=account.id, balance_cents=0)
            self.session.add(balance)
        balance.balance_cents = balance.balance_cents + delta_cents

    def _status_id(self, model, enumerator: str) -> int:
        return self.session.query(model.id).filter(model.enumerator == enumerator).scalar()
