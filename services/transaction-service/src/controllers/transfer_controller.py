import hashlib
import json

from controllers.base_controller import BaseController
from errors import AccountNotAvailable, AccountNotFound, DestinationNotFound, IdempotencyConflict, InsufficientBalance
from errors.base_error import InvalidSchema
from repositories import TransactionRepository
from utils.fee import calcular_tarifa


class TransferController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.transaction_repository = TransactionRepository(self.context)

    def create(self, account_key: str, transfer_data: dict, idempotency_key: str) -> dict:
        if not idempotency_key:
            raise InvalidSchema("O cabeçalho Idempotency-Key é obrigatório.")

        origin = self.transaction_repository.get_account_by_key(account_key)
        requester = self.transaction_repository.get_customer_by_key(transfer_data["customer_key"])

        if origin is None or requester is None or not self.transaction_repository.is_active_holder(origin, requester):
            raise AccountNotFound(account_key)

        request_hash = hashlib.sha256(json.dumps(transfer_data, sort_keys=True).encode()).hexdigest()
        previous = self.transaction_repository.get_transfer_by_idempotency(origin, idempotency_key)
        if previous is not None:
            if previous.request_hash != request_hash:
                raise IdempotencyConflict(idempotency_key)
            return self._response(previous)

        if self.transaction_repository.account_status_enumerator(origin) != "ACTIVE":
            raise AccountNotAvailable(account_key)

        destination = self.transaction_repository.get_account_by_number(transfer_data["destination_account_number"])
        verified_customer = self.transaction_repository.get_customer_by_document(transfer_data["destination_document_number"])
        if destination is None or verified_customer is None:
            raise DestinationNotFound()

        verified_holder = self.transaction_repository.get_active_holder(destination, verified_customer)
        if verified_holder is None:
            raise DestinationNotFound()

        amount_cents = transfer_data["amount_cents"]
        adult_count = self.transaction_repository.count_active_adults(origin)
        fee_cents = calcular_tarifa(amount_cents, adult_count)

        if self.transaction_repository.get_balance(origin) < amount_cents + fee_cents:
            raise InsufficientBalance(account_key)

        transfer = self.transaction_repository.create_transfer(
            origin, destination, requester, verified_holder, amount_cents, fee_cents, adult_count,
            idempotency_key, request_hash,
        )
        self.session.commit()

        return self._response(transfer)

    @staticmethod
    def _response(transfer) -> dict:
        return {
            "transaction_key": transfer.transaction_key,
            "amount_cents": transfer.amount_cents,
            "fee_cents": transfer.fee_cents,
            "total_cents": transfer.amount_cents + transfer.fee_cents,
        }
