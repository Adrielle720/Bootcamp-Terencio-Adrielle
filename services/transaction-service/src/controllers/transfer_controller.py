from controllers.base_controller import BaseController
from errors import (
    AccountNotAvailable,
    AccountNotFound,
    DestinationNotAvailable,
    DestinationNotFound,
    IdempotencyConflict,
    InsufficientBalance,
    InvalidAccountNumber,
    MonthlyLimitExceeded,
    SameAccountTransfer,
    TransferLimitExceeded,
)
from errors.base_error import InvalidSchema
from repositories import TransactionRepository
from repositories.transaction_repository import FEE_REVENUE_ACCOUNT_KEY
from utils.account_number import has_valid_check_digit
from utils.age import is_adult
from utils.fee import calcular_tarifa
from utils.request_hash import request_hash

RECEIVING_STATUSES = ["ACTIVE", "BLOCKED", "CLOSING"]


class TransferController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.transaction_repository = TransactionRepository(self.context)

    def create(self, account_key: str, transfer_data: dict, idempotency_key: str) -> dict:
        if not idempotency_key:
            raise InvalidSchema("O cabeçalho Idempotency-Key é obrigatório.")

        origin = self.transaction_repository.get_customer_account_by_key(account_key)
        requester = self.transaction_repository.get_customer_by_key(transfer_data["customer_key"])
        requester_holder = self.transaction_repository.get_active_holder(origin, requester)
        if requester_holder is None:
            raise AccountNotFound(account_key)

        body_hash = request_hash(transfer_data)
        previous = self._previous(origin, idempotency_key, body_hash)
        if previous is not None:
            return previous

        if self.transaction_repository.account_status(origin) != "ACTIVE":
            raise AccountNotAvailable(account_key)

        destination, verified_holder = self._resolve_destination(transfer_data)
        if destination.id == origin.id:
            raise SameAccountTransfer()

        amount_cents = transfer_data["amount_cents"]
        adult_count = self.transaction_repository.count_active_adults(origin)
        fee_cents = calcular_tarifa(amount_cents, adult_count)

        if origin.transfer_limit_cents is not None and amount_cents > origin.transfer_limit_cents:
            raise TransferLimitExceeded(account_key)

        # Daqui até o commit, uma operação por conta: a segunda espera a
        # primeira terminar e lê o saldo já atualizado.
        revenue = self.transaction_repository.get_institution_account(FEE_REVENUE_ACCOUNT_KEY)
        self.transaction_repository.lock_balances([origin, destination, revenue])
        previous = self._previous(origin, idempotency_key, body_hash)
        if previous is not None:
            return previous

        if self._is_restricted_minor(requester_holder, requester):
            spent = self.transaction_repository.minor_spent_this_month(origin, requester)
            if spent + amount_cents + fee_cents > requester_holder.monthly_limit_cents:
                raise MonthlyLimitExceeded(account_key)

        if self.transaction_repository.get_balance(origin) < amount_cents + fee_cents:
            raise InsufficientBalance(account_key)

        transfer = self.transaction_repository.create_transfer(
            origin, destination, requester, verified_holder, amount_cents, fee_cents, adult_count,
            idempotency_key, body_hash,
        )
        self.session.commit()

        return self._response(transfer)

    def _resolve_destination(self, transfer_data: dict):
        """Número da conta e CPF de um titular ativo dela.

        Conta inexistente, conta da instituição e CPF que não é de titular
        dão o mesmo 404: quem testa combinações não descobre qual parte errou.
        """
        account_number = transfer_data["destination_account_number"]
        if not has_valid_check_digit(account_number):
            raise InvalidAccountNumber(account_number)

        destination = self.transaction_repository.get_customer_account_by_number(account_number)
        verified_customer = self.transaction_repository.get_customer_by_document(
            transfer_data["destination_document_number"])
        verified_holder = self.transaction_repository.get_active_holder(destination, verified_customer)
        if verified_holder is None:
            raise DestinationNotFound()

        if self.transaction_repository.account_status(destination) not in RECEIVING_STATUSES:
            raise DestinationNotAvailable()

        return destination, verified_holder

    @staticmethod
    def _is_restricted_minor(holder, customer) -> bool:
        # Ao completar 18 anos as restrições caem sozinhas: a idade vem da
        # data de nascimento, nunca de um papel gravado.
        return holder.role == "MINOR" and holder.monthly_limit_cents is not None and not is_adult(customer.birthdate)

    def _previous(self, origin, idempotency_key: str, body_hash: str):
        previous = self.transaction_repository.get_transfer_by_idempotency(origin, idempotency_key)
        if previous is None:
            return None
        if previous.request_hash != body_hash:
            raise IdempotencyConflict(idempotency_key)
        return self._response(previous)

    @staticmethod
    def _response(transfer) -> dict:
        return {
            "transfer_key": transfer.transfer_key,
            "amount_cents": transfer.amount_cents,
            "fee_cents": transfer.fee_cents,
            "total_cents": transfer.amount_cents + transfer.fee_cents,
            "created_at": transfer.created_at.isoformat(),
        }
