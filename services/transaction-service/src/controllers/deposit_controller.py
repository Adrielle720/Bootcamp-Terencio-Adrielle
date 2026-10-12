from controllers.base_controller import BaseController
from errors import AccountNotAvailable, AccountNotFound, IdempotencyConflict
from repositories import TransactionRepository
from repositories.transaction_repository import SETTLEMENT_ACCOUNT_KEY
from utils.request_hash import request_hash

DEPOSITABLE_STATUSES = ["ACTIVE", "BLOCKED", "CLOSING"]


class DepositController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.transaction_repository = TransactionRepository(self.context)

    def create(self, account_key: str, deposit_data: dict, idempotency_key: str = None) -> dict:
        account = self.transaction_repository.get_customer_account_by_key(account_key)
        customer = self.transaction_repository.get_customer_by_key(deposit_data["customer_key"])
        if self.transaction_repository.get_active_holder(account, customer) is None:
            raise AccountNotFound(account_key)

        body_hash = request_hash(deposit_data)
        previous = self._previous(account, idempotency_key, body_hash)
        if previous is not None:
            return previous

        if self.transaction_repository.account_status(account) not in DEPOSITABLE_STATUSES:
            raise AccountNotAvailable(account_key)

        settlement = self.transaction_repository.get_institution_account(SETTLEMENT_ACCOUNT_KEY)
        self.transaction_repository.lock_balances([settlement, account])
        previous = self._previous(account, idempotency_key, body_hash)
        if previous is not None:
            return previous

        deposit = self.transaction_repository.create_deposit(
            account, customer, deposit_data["amount_cents"], idempotency_key, body_hash)
        self.session.commit()

        return self._response(deposit)

    def _previous(self, account, idempotency_key: str, body_hash: str):
        if idempotency_key is None:
            return None

        previous = self.transaction_repository.get_deposit_by_idempotency(account, idempotency_key)
        if previous is None:
            return None
        if previous.request_hash != body_hash:
            raise IdempotencyConflict(idempotency_key)
        return self._response(previous)

    @staticmethod
    def _response(deposit) -> dict:
        return {
            "deposit_key": deposit.deposit_key,
            "amount_cents": deposit.amount_cents,
            "created_at": deposit.created_at.isoformat(),
        }
