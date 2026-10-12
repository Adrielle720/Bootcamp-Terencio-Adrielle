from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, or_, text

from constants import FEE_REVENUE_ACCOUNT_KEY, SETTLEMENT_ACCOUNT_KEY
from database import Context
from models import (
    AccountBalance,
    BalanceType,
    Deposit,
    EntryType,
    FeeTier,
    LedgerEntry,
    Notification,
    NotificationType,
    Transfer,
)

# O mês do limite do menor é o do calendário em São Paulo. created_at é
# gravado em UTC, por isso a conversão dos dois lados.
SAO_PAULO_MONTH_FILTER = text(
    "(transfers.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo') "
    ">= date_trunc('month', NOW() AT TIME ZONE 'America/Sao_Paulo')"
)


def utc_now() -> datetime:
    """O instante em UTC, sem fuso, como as colunas TIMESTAMP guardam."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session
        self._ids = {}

    # ── saldos ─────────────────────────────────────────────────────────

    def lock_balances(self, account_keys: list) -> dict:
        """Cria os saldos que faltam e trava todos, sempre do menor id para o maior.

        Duas transferências cruzadas (A→B e B→A) travam na mesma ordem, e a
        segunda espera a primeira em vez de as duas esperarem uma pela outra
        para sempre. Devolve os saldos travados, por account_key.
        """
        customer_type = self.domain_id(BalanceType, "CUSTOMER")
        for account_key in set(account_keys):
            self.session.execute(text(
                "INSERT INTO account_balances (account_key, balance_type_id, balance_cents) "
                "VALUES (:account_key, :balance_type_id, 0) ON CONFLICT (account_key) DO NOTHING"
            ), {"account_key": account_key, "balance_type_id": customer_type})

        balances = (
            self.session.query(AccountBalance)
            .filter(AccountBalance.account_key.in_(set(account_keys)))
            .order_by(AccountBalance.id)
            .with_for_update()
            .all()
        )
        return {balance.account_key: balance for balance in balances}

    def get_balance(self, account_key: str) -> int:
        balance = self.session.query(AccountBalance.balance_cents).filter(
            AccountBalance.account_key == account_key).scalar()
        return balance if balance is not None else 0

    def institution_balances(self) -> dict:
        return {
            "fee_revenue_cents": self.get_balance(FEE_REVENUE_ACCOUNT_KEY),
            "settlement_cents": self.get_balance(SETTLEMENT_ACCOUNT_KEY),
        }

    # ── regras de dinheiro ─────────────────────────────────────────────

    def base_fee_for(self, amount_cents: int) -> int:
        tier = self.session.query(FeeTier).filter(
            FeeTier.min_amount_cents <= amount_cents,
            or_(FeeTier.max_amount_cents.is_(None), FeeTier.max_amount_cents >= amount_cents),
        ).first()
        return tier.base_fee_cents

    def spent_this_month(self, origin_account_key: str, requester_customer_key: str) -> int:
        spent = self.session.query(func.coalesce(func.sum(Transfer.amount_cents + Transfer.fee_cents), 0)).filter(
            Transfer.origin_account_key == origin_account_key,
            Transfer.requester_customer_key == requester_customer_key,
            SAO_PAULO_MONTH_FILTER,
        ).scalar()
        return int(spent)

    # ── operações ──────────────────────────────────────────────────────

    def create_deposit(self, balances: dict, context: dict, amount_cents: int) -> Deposit:
        now = utc_now()
        deposit = Deposit()
        deposit.deposit_key = str(uuid4())
        deposit.account_key = context["account_key"]
        deposit.depositor_customer_key = context["requester"]["customer_key"]
        deposit.depositor_name = context["requester"]["name"]
        deposit.amount_cents = amount_cents
        deposit.created_at = now
        self.session.add(deposit)
        self.session.flush()

        self._post(balances[SETTLEMENT_ACCOUNT_KEY], "SETTLEMENT_DEBIT", -amount_cents, now, deposit_id=deposit.id)
        self._post(balances[context["account_key"]], "DEPOSIT_CREDIT", amount_cents, now, deposit_id=deposit.id)
        return deposit

    def create_transfer(self, balances: dict, origin: dict, destination: dict, amount_cents: int,
                        fee_cents: int) -> Transfer:
        now = utc_now()
        transfer = Transfer()
        transfer.transfer_key = str(uuid4())
        transfer.origin_account_key = origin["account_key"]
        transfer.destination_account_key = destination["account_key"]
        transfer.requester_customer_key = origin["requester"]["customer_key"]
        transfer.requester_name = origin["requester"]["name"]
        transfer.origin_account_number = origin["account_number"]
        transfer.destination_account_number = destination["account_number"]
        transfer.verified_holder_name = destination["verified_holder"]["name"]
        transfer.amount_cents = amount_cents
        transfer.fee_cents = fee_cents
        transfer.adult_count = origin["adult_count"]
        transfer.created_at = now
        self.session.add(transfer)
        self.session.flush()

        origin_balance = balances[origin["account_key"]]
        self._post(origin_balance, "TRANSFER_DEBIT", -amount_cents, now, transfer_id=transfer.id)
        self._post(origin_balance, "FEE_DEBIT", -fee_cents, now, transfer_id=transfer.id)
        self._post(balances[destination["account_key"]], "TRANSFER_CREDIT", amount_cents, now, transfer_id=transfer.id)
        self._post(balances[FEE_REVENUE_ACCOUNT_KEY], "FEE_CREDIT", fee_cents, now, transfer_id=transfer.id)
        return transfer

    def notify(self, holders: list, account_key: str, notification_type: str, payload: dict) -> None:
        """Notificação só dentro do app: linhas gravadas no mesmo commit da operação."""
        type_id = self.domain_id(NotificationType, notification_type)
        for holder in holders:
            notification = Notification()
            notification.notification_key = str(uuid4())
            notification.customer_key = holder["customer_key"]
            notification.account_key = account_key
            notification.notification_type_id = type_id
            notification.payload = payload
            self.session.add(notification)

    def _post(self, balance: AccountBalance, entry_type: str, amount_cents: int, now: datetime,
              deposit_id: int = None, transfer_id: int = None) -> None:
        """Um lançamento no ledger e o saldo atualizado, no mesmo commit.

        O saldo só muda por aqui: assim ele é sempre a soma dos lançamentos, e
        a tabela de saldo existe só para a checagem ser rápida.
        """
        entry = LedgerEntry()
        entry.account_balance_id = balance.id
        entry.deposit_id = deposit_id
        entry.transfer_id = transfer_id
        entry.entry_type_id = self.domain_id(EntryType, entry_type)
        entry.amount_cents = amount_cents
        entry.created_at = now
        self.session.add(entry)

        balance.balance_cents = balance.balance_cents + amount_cents
        balance.updated_at = now

    def domain_id(self, model, enumerator: str) -> int:
        cache_key = (model.__tablename__, enumerator)
        if cache_key not in self._ids:
            self._ids[cache_key] = self.session.query(model.id).filter(model.enumerator == enumerator).scalar()
        return self._ids[cache_key]
