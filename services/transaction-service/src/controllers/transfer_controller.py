from sqlalchemy.exc import IntegrityError

from connectors import AccountConnector
from constants import FEE_REVENUE_ACCOUNT_KEY
from controllers.idempotent_controller import IdempotentController
from errors import (
    AccountNotAvailable,
    AccountNotFound,
    DestinationNotAvailable,
    DestinationNotFound,
    InsufficientBalance,
    InvalidAccountNumber,
    MonthlyLimitExceeded,
    SameAccountTransfer,
    TransferLimitExceeded,
)
from errors.base_error import InvalidSchema
from repositories import TransactionRepository
from utils.account_number import has_valid_check_digit
from utils.request_hash import request_hash

RECEIVING_STATUSES = ["ACTIVE", "BLOCKED", "CLOSING"]
FREE_ADULTS = 2
EXTRA_FEE_PER_ADULT_CENTS = 50


class TransferController(IdempotentController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.transaction_repository = TransactionRepository(self.context)
        self.account_connector = AccountConnector()

    def create(self, account_key: str, transfer_data: dict, idempotency_key: str) -> dict:
        if not idempotency_key:
            raise InvalidSchema("O cabeçalho Idempotency-Key é obrigatório.")

        scope = f"{account_key} POST /transfers"
        body_hash = request_hash(transfer_data)
        previous = self.previous_response(scope, idempotency_key, body_hash)
        if previous is not None:
            return previous

        # Tudo o que vem de outro serviço é lido antes de qualquer trava. Se o
        # account-service não responde, é 503 e nada foi gravado.
        origin = self.account_connector.context(account_key, transfer_data["customer_key"])
        if origin is None:
            raise AccountNotFound(account_key)
        if origin["status"] != "ACTIVE":
            raise AccountNotAvailable(account_key)

        destination = self._resolve_destination(transfer_data)
        if destination["account_key"] == origin["account_key"]:
            raise SameAccountTransfer()

        # Daqui até o commit, uma operação por conta: a segunda espera a
        # primeira terminar e lê o saldo já atualizado.
        balances = self.transaction_repository.lock_balances(
            [origin["account_key"], destination["account_key"], FEE_REVENUE_ACCOUNT_KEY])
        previous = self.previous_response(scope, idempotency_key, body_hash)
        if previous is not None:
            return previous

        amount_cents = transfer_data["amount_cents"]
        fee_cents = self._fee(amount_cents, origin["adult_count"])

        if origin["transfer_limit_cents"] is not None and amount_cents > origin["transfer_limit_cents"]:
            raise TransferLimitExceeded(account_key)

        requester = origin["requester"]
        if requester["role"] == "MINOR" and requester["is_minor"] and requester["monthly_limit_cents"] is not None:
            spent = self.transaction_repository.spent_this_month(account_key, requester["customer_key"])
            if spent + amount_cents + fee_cents > requester["monthly_limit_cents"]:
                raise MonthlyLimitExceeded(account_key)

        if balances[account_key].balance_cents < amount_cents + fee_cents:
            raise InsufficientBalance(account_key)

        transfer = self.transaction_repository.create_transfer(balances, origin, destination, amount_cents, fee_cents)
        payload = {"transfer_key": transfer.transfer_key, "amount_cents": amount_cents}
        self.transaction_repository.notify(origin["active_holders"], origin["account_key"], "TRANSFER_SENT",
                                           {**payload, "fee_cents": fee_cents,
                                            "destination_account_number": destination["account_number"]})
        self.transaction_repository.notify(destination["active_holders"], destination["account_key"],
                                           "TRANSFER_RECEIVED",
                                           {**payload, "origin_account_number": origin["account_number"]})
        response = {
            "transfer_key": transfer.transfer_key,
            "amount_cents": amount_cents,
            "fee_cents": fee_cents,
            "total_cents": amount_cents + fee_cents,
            "created_at": transfer.created_at.isoformat(),
        }
        self.remember_response(scope, idempotency_key, body_hash, response)

        try:
            self.session.commit()
        except IntegrityError:
            # Repetição concorrente com a mesma chave: a primeira gravou, esta
            # esbarrou no UNIQUE. Devolve a resposta guardada, nunca 500.
            self.session.rollback()
            previous = self.previous_response(scope, idempotency_key, body_hash)
            if previous is not None:
                return previous
            raise

        return response

    def _resolve_destination(self, transfer_data: dict) -> dict:
        """Número da conta e CPF de um titular ativo dela.

        O dígito verificador é conferido sem consultar ninguém. Conta
        inexistente, conta da instituição e CPF que não é de titular dão o
        mesmo 404: quem testa combinações não descobre qual parte errou.
        """
        account_number = transfer_data["destination_account_number"]
        if not has_valid_check_digit(account_number):
            raise InvalidAccountNumber(account_number)

        destination = self.account_connector.destination(account_number, transfer_data["destination_document_number"])
        if destination is None:
            raise DestinationNotFound()
        if destination["status"] not in RECEIVING_STATUSES:
            raise DestinationNotAvailable()
        return destination

    def _fee(self, amount_cents: int, adult_count: int) -> int:
        """Base da faixa + máx(0, adultos ativos − 2) × R$ 0,50. Menores não contam."""
        extra_adults = max(0, adult_count - FREE_ADULTS)
        return self.transaction_repository.base_fee_for(amount_cents) + extra_adults * EXTRA_FEE_PER_ADULT_CENTS
