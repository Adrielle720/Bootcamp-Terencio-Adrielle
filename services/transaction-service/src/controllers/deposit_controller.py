from sqlalchemy.exc import IntegrityError

from connectors import AccountConnector
from constants import SETTLEMENT_ACCOUNT_KEY
from controllers.idempotent_controller import IdempotentController
from errors import AccountNotAvailable, AccountNotFound
from repositories import TransactionRepository
from utils.request_hash import request_hash

DEPOSITABLE_STATUSES = ["ACTIVE", "BLOCKED", "CLOSING"]


class DepositController(IdempotentController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.transaction_repository = TransactionRepository(self.context)

    def create(self, account_key: str, deposit_data: dict, idempotency_key: str = None) -> dict:
        scope = f"{account_key} POST /deposits"
        body_hash = request_hash(deposit_data)
        previous = self.previous_response(scope, idempotency_key, body_hash)
        if previous is not None:
            return previous

        # O contexto vem do account-service antes de qualquer trava.
        context = AccountConnector().context(account_key, deposit_data["customer_key"])
        if context is None:
            raise AccountNotFound(account_key)
        if context["status"] not in DEPOSITABLE_STATUSES:
            raise AccountNotAvailable(account_key)

        # Uma operação por conta de cada vez, e a repetição concorrente da
        # mesma chave enxerga a primeira depois de esperar a trava.
        balances = self.transaction_repository.lock_balances([SETTLEMENT_ACCOUNT_KEY, account_key])
        previous = self.previous_response(scope, idempotency_key, body_hash)
        if previous is not None:
            return previous

        deposit = self.transaction_repository.create_deposit(balances, context, deposit_data["amount_cents"])
        self.transaction_repository.notify(context["active_holders"], account_key, "DEPOSIT_RECEIVED",
                                           {"deposit_key": deposit.deposit_key, "amount_cents": deposit.amount_cents,
                                            "depositor_name": deposit.depositor_name})
        response = {
            "deposit_key": deposit.deposit_key,
            "amount_cents": deposit.amount_cents,
            "created_at": deposit.created_at.isoformat(),
        }
        self.remember_response(scope, idempotency_key, body_hash, response)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            previous = self.previous_response(scope, idempotency_key, body_hash)
            if previous is not None:
                return previous
            raise

        return response
