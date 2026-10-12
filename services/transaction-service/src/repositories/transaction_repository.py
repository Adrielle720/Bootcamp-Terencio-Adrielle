from uuid import uuid4

from sqlalchemy import func, text

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
from utils.age import is_adult

# As duas contas da instituição, criadas no database.sql.
FEE_REVENUE_ACCOUNT_KEY = "00000000-0000-0000-0000-000000000001"
SETTLEMENT_ACCOUNT_KEY = "00000000-0000-0000-0000-000000000002"

# O mês do limite do menor é o do calendário em São Paulo. created_at é
# gravado em UTC (o NOW() do Postgres no container), por isso a conversão.
SAO_PAULO_MONTH_FILTER = text(
    "(transfer.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo') "
    ">= date_trunc('month', NOW() AT TIME ZONE 'America/Sao_Paulo')"
)


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session
        self._status_ids = {}

    # ── contas e titulares ─────────────────────────────────────────────

    def get_customer_account_by_key(self, account_key: str) -> Account:
        return self.session.query(Account).filter(
            Account.account_key == account_key,
            Account.is_institution.is_(False),
        ).first()

    def get_customer_account_by_number(self, account_number: str) -> Account:
        return self.session.query(Account).filter(
            Account.account_number == account_number,
            Account.is_institution.is_(False),
        ).first()

    def get_institution_account(self, account_key: str) -> Account:
        return self.session.query(Account).filter(Account.account_key == account_key).one()

    def get_customer_by_key(self, customer_key: str) -> Customer:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_customer_by_document(self, document_number: str) -> Customer:
        return self.session.query(Customer).filter(Customer.document_number == document_number).first()

    def get_active_holder(self, account: Account, customer: Customer) -> AccountHolder:
        if account is None or customer is None:
            return None
        return self.session.query(AccountHolder).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.customer_id == customer.id,
            AccountHolder.status_id == self._status_id(HolderStatus, "ACTIVE"),
        ).first()

    def count_active_adults(self, account: Account) -> int:
        birthdates = (
            self.session.query(Customer.birthdate)
            .join(AccountHolder, AccountHolder.customer_id == Customer.id)
            .filter(
                AccountHolder.account_id == account.id,
                AccountHolder.status_id == self._status_id(HolderStatus, "ACTIVE"),
            )
            .all()
        )
        return sum(1 for (birthdate,) in birthdates if is_adult(birthdate))

    def account_status(self, account: Account) -> str:
        return self.session.query(AccountStatus.enumerator).filter(AccountStatus.id == account.status_id).scalar()

    # ── idempotência ───────────────────────────────────────────────────

    def get_deposit_by_idempotency(self, account: Account, idempotency_key: str) -> Deposit:
        return self.session.query(Deposit).filter(
            Deposit.account_id == account.id,
            Deposit.idempotency_key == idempotency_key,
        ).first()

    def get_transfer_by_idempotency(self, origin: Account, idempotency_key: str) -> Transfer:
        return self.session.query(Transfer).filter(
            Transfer.origin_account_id == origin.id,
            Transfer.idempotency_key == idempotency_key,
        ).first()

    # ── saldos ─────────────────────────────────────────────────────────

    def lock_balances(self, accounts: list) -> None:
        """Trava os saldos sempre do menor id para o maior.

        Duas transferências cruzadas (A→B e B→A) travam na mesma ordem, e
        a segunda espera a primeira em vez de as duas esperarem uma pela
        outra para sempre. O saldo que ainda não existe nasce zerado antes
        de ser travado, para haver uma linha a travar.
        """
        account_ids = sorted({account.id for account in accounts})
        for account_id in account_ids:
            self.session.execute(text(
                "INSERT INTO account_balance (account_id, balance_cents) VALUES (:account_id, 0) "
                "ON CONFLICT (account_id) DO NOTHING"
            ), {"account_id": account_id})
            self.session.query(AccountBalance).filter(AccountBalance.account_id == account_id).with_for_update().one()

    def get_balance(self, account: Account) -> int:
        balance = self.session.query(AccountBalance.balance_cents).filter(AccountBalance.account_id == account.id).scalar()
        return balance if balance is not None else 0

    def minor_spent_this_month(self, origin: Account, requester: Customer) -> int:
        spent = self.session.query(func.coalesce(func.sum(Transfer.amount_cents + Transfer.fee_cents), 0)).filter(
            Transfer.origin_account_id == origin.id,
            Transfer.requested_by_id == requester.id,
            SAO_PAULO_MONTH_FILTER,
        ).scalar()
        return int(spent)

    # ── operações ──────────────────────────────────────────────────────

    def create_deposit(self, account: Account, customer: Customer, amount_cents: int,
                       idempotency_key: str, request_hash: str) -> Deposit:
        deposit = Deposit()
        deposit.deposit_key = str(uuid4())
        deposit.account_id = account.id
        deposit.customer_id = customer.id
        deposit.amount_cents = amount_cents
        deposit.idempotency_key = idempotency_key
        deposit.request_hash = request_hash
        self.session.add(deposit)
        self.session.flush()

        settlement = self.get_institution_account(SETTLEMENT_ACCOUNT_KEY)
        self._post(settlement, "SETTLEMENT_DEBIT", -amount_cents, deposit_id=deposit.id)
        self._post(account, "DEPOSIT_CREDIT", amount_cents, deposit_id=deposit.id)

        return deposit

    def create_transfer(self, origin: Account, destination: Account, requester: Customer,
                        verified_holder: AccountHolder, amount_cents: int, fee_cents: int,
                        adult_count: int, idempotency_key: str, request_hash: str) -> Transfer:
        transfer = Transfer()
        transfer.transfer_key = str(uuid4())
        transfer.origin_account_id = origin.id
        transfer.destination_account_id = destination.id
        transfer.requested_by_id = requester.id
        transfer.verified_holder_id = verified_holder.id
        transfer.amount_cents = amount_cents
        transfer.fee_cents = fee_cents
        transfer.adult_count = adult_count
        transfer.idempotency_key = idempotency_key
        transfer.request_hash = request_hash
        self.session.add(transfer)
        self.session.flush()

        revenue = self.get_institution_account(FEE_REVENUE_ACCOUNT_KEY)
        self._post(origin, "TRANSFER_DEBIT", -amount_cents, transfer_id=transfer.id)
        self._post(origin, "FEE_DEBIT", -fee_cents, transfer_id=transfer.id)
        self._post(destination, "TRANSFER_CREDIT", amount_cents, transfer_id=transfer.id)
        self._post(revenue, "FEE_CREDIT", fee_cents, transfer_id=transfer.id)

        return transfer

    def institution_balances(self) -> dict:
        return {
            "fee_revenue_cents": self.get_balance(self.get_institution_account(FEE_REVENUE_ACCOUNT_KEY)),
            "settlement_cents": self.get_balance(self.get_institution_account(SETTLEMENT_ACCOUNT_KEY)),
        }

    def _post(self, account: Account, entry_type: str, amount_cents: int, deposit_id: int = None,
              transfer_id: int = None) -> None:
        """Um lançamento no ledger e o saldo atualizado, no mesmo commit.

        O saldo só pode mudar por aqui: assim ele é sempre a soma dos
        lançamentos, e a tabela de saldo existe só para a checagem ser rápida.
        """
        self.session.add(LedgerEntry(account_id=account.id, deposit_id=deposit_id, transfer_id=transfer_id,
                                     entry_type=entry_type, amount_cents=amount_cents))
        balance = self.session.query(AccountBalance).filter(AccountBalance.account_id == account.id).one()
        balance.balance_cents = balance.balance_cents + amount_cents
        balance.updated_at = func.now()

    def _status_id(self, model, enumerator: str) -> int:
        cache_key = (model.__tablename__, enumerator)
        if cache_key not in self._status_ids:
            self._status_ids[cache_key] = self.session.query(model.id).filter(model.enumerator == enumerator).scalar()
        return self._status_ids[cache_key]
