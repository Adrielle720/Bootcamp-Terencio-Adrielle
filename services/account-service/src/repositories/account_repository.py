from datetime import datetime
from uuid import uuid4

from sqlalchemy import and_, or_

from database import Context
from models import Account, AccountBalance, AccountEvent, AccountHolder, AccountStatus, Customer, HolderStatus
from utils.account_number import gerar_numero_da_conta

# Vínculos que ocupam vaga e prendem a pessoa a esta conta.
OPEN_HOLDER_STATUSES = ["INVITED", "ACTIVE", "PENDING_GUARDIANSHIP"]


class AccountRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session
        self._status_ids = {}

    # ── clientes ───────────────────────────────────────────────────────

    def get_customer_by_key(self, customer_key: str) -> Customer:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_customer_by_contact(self, email: str = None, phone: str = None) -> Customer:
        if email is not None:
            return self.session.query(Customer).filter(Customer.email == email).first()
        return self.session.query(Customer).filter(Customer.phone == phone).first()

    # ── contas ─────────────────────────────────────────────────────────

    def get_account_by_key(self, account_key: str, lock: bool = False) -> Account:
        query = self.session.query(Account).filter(
            Account.account_key == account_key,
            Account.is_institution.is_(False),
        )
        if lock:
            query = query.with_for_update()
        return query.first()

    def get_account_by_id(self, account_id: int, lock: bool = False) -> Account:
        query = self.session.query(Account).filter(Account.id == account_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def create_account(self, name: str, actor_customer_key: str) -> Account:
        account = Account()
        account.account_key = str(uuid4())
        account.account_number = self._new_account_number()
        account.name = name
        account.status_id = self.status_id(AccountStatus, "PENDING")
        self.session.add(account)
        self.session.flush()

        self.add_event(account, "PENDING", actor_customer_key, "Conta aberta pelo master")
        return account

    def account_status(self, account: Account) -> str:
        return self.enumerator_of(AccountStatus, account.status_id)

    def set_account_status(self, account: Account, enumerator: str, actor_customer_key: str, reason: str) -> None:
        account.status_id = self.status_id(AccountStatus, enumerator)
        self.add_event(account, enumerator, actor_customer_key, reason)

    def add_event(self, account: Account, enumerator: str, actor_customer_key: str, reason: str) -> None:
        event = AccountEvent()
        event.account_id = account.id
        event.status_id = self.status_id(AccountStatus, enumerator)
        event.actor_customer_key = actor_customer_key
        event.reason = reason
        self.session.add(event)

    def cancel_account(self, account: Account, actor_customer_key: str, reason: str) -> None:
        """Cancela a conta e solta todo mundo que estava preso a ela.

        Convite pendente vira CANCELED; quem já estava dentro (o master, um
        menor esperando a guarda) vira LEFT. Sem isso, o índice único de
        uma conta por pessoa não deixaria o master abrir outra.
        """
        now = datetime.now()
        for holder in self.open_holders_of(account):
            if self.holder_status(holder) == "INVITED":
                holder.status_id = self.status_id(HolderStatus, "CANCELED")
            else:
                holder.status_id = self.status_id(HolderStatus, "LEFT")
                holder.left_at = now

        self.set_account_status(account, "CANCELED", actor_customer_key, reason)

    def cancel_if_no_invite_left(self, account: Account, actor_customer_key: str, reason: str) -> None:
        self.session.flush()
        if self.account_status(account) == "PENDING" and not self.has_invited_holders(account):
            self.cancel_account(account, actor_customer_key, reason)

    def balance_of(self, account: Account) -> int:
        balance = self.session.query(AccountBalance.balance_cents).filter(AccountBalance.account_id == account.id).scalar()
        return balance if balance is not None else 0

    # ── titulares e convites ───────────────────────────────────────────

    def get_holder_by_key(self, holder_key: str, lock: bool = False) -> AccountHolder:
        query = self.session.query(AccountHolder).filter(AccountHolder.holder_key == holder_key)
        if lock:
            query = query.with_for_update()
        return query.first()

    def get_active_holder(self, account: Account, customer: Customer) -> AccountHolder:
        if account is None or customer is None:
            return None
        return self.session.query(AccountHolder).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.customer_id == customer.id,
            AccountHolder.status_id == self.status_id(HolderStatus, "ACTIVE"),
        ).first()

    def was_master_of(self, account: Account, customer: Customer) -> bool:
        if account is None or customer is None:
            return False
        return self.session.query(AccountHolder.id).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.customer_id == customer.id,
            AccountHolder.role == "MASTER",
        ).first() is not None

    def holders_of(self, account: Account) -> list:
        return (
            self.session.query(AccountHolder, Customer)
            .outerjoin(Customer, AccountHolder.customer_id == Customer.id)
            .filter(AccountHolder.account_id == account.id)
            .order_by(AccountHolder.id)
            .all()
        )

    def open_holders_of(self, account: Account) -> list:
        return self.session.query(AccountHolder).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.status_id.in_(self._open_status_ids()),
        ).all()

    def count_seats(self, account: Account) -> int:
        return len(self.open_holders_of(account))

    def has_invited_holders(self, account: Account) -> bool:
        return self.session.query(AccountHolder.id).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.status_id == self.status_id(HolderStatus, "INVITED"),
        ).first() is not None

    def has_open_holder(self, customer: Customer) -> bool:
        """A pessoa já está presa a alguma conta: dentro dela, ou convidada.

        O convite pode estar ligado à customer_key ou, se foi feito antes
        do cadastro, só ao e-mail ou celular que ela usa hoje.
        """
        by_customer = self.session.query(AccountHolder.id).filter(
            AccountHolder.customer_id == customer.id,
            AccountHolder.status_id.in_(self._open_status_ids()),
        ).first()
        return by_customer is not None or len(self.contact_invitations_of(customer)) > 0

    def has_joined_account(self, customer: Customer) -> bool:
        return self.session.query(AccountHolder.id).filter(
            AccountHolder.customer_id == customer.id,
            AccountHolder.status_id.in_([
                self.status_id(HolderStatus, "ACTIVE"),
                self.status_id(HolderStatus, "PENDING_GUARDIANSHIP"),
            ]),
        ).first() is not None

    def has_pending_invite_for_contact(self, email: str = None, phone: str = None) -> bool:
        contact_filter = AccountHolder.invited_email == email if email is not None else AccountHolder.invited_phone == phone
        return self.session.query(AccountHolder.id).filter(
            AccountHolder.customer_id.is_(None),
            AccountHolder.status_id == self.status_id(HolderStatus, "INVITED"),
            contact_filter,
        ).first() is not None

    def contact_invitations_of(self, customer: Customer) -> list:
        return self.session.query(AccountHolder).filter(
            AccountHolder.customer_id.is_(None),
            AccountHolder.status_id == self.status_id(HolderStatus, "INVITED"),
            or_(AccountHolder.invited_email == customer.email, AccountHolder.invited_phone == customer.phone),
        ).all()

    def pending_invitations_of(self, customer: Customer) -> list:
        return (
            self.session.query(AccountHolder, Account)
            .join(Account, AccountHolder.account_id == Account.id)
            .filter(
                AccountHolder.status_id == self.status_id(HolderStatus, "INVITED"),
                or_(
                    AccountHolder.customer_id == customer.id,
                    and_(
                        AccountHolder.customer_id.is_(None),
                        or_(AccountHolder.invited_email == customer.email,
                            AccountHolder.invited_phone == customer.phone),
                    ),
                ),
            )
            .order_by(AccountHolder.invited_at.desc())
            .all()
        )

    def invitation_belongs_to(self, holder: AccountHolder, customer: Customer) -> bool:
        if holder.customer_id is not None:
            return holder.customer_id == customer.id
        return holder.invited_email == customer.email or holder.invited_phone == customer.phone

    def add_holder(self, account: Account, role: str, status: str, customer: Customer = None,
                   email: str = None, phone: str = None) -> AccountHolder:
        holder = AccountHolder()
        holder.holder_key = str(uuid4())
        holder.account_id = account.id
        holder.customer_id = customer.id if customer is not None else None
        holder.role = role
        holder.status_id = self.status_id(HolderStatus, status)
        holder.invited_email = email
        holder.invited_phone = phone
        if status == "ACTIVE":
            holder.joined_at = datetime.now()
        self.session.add(holder)
        return holder

    def holder_status(self, holder: AccountHolder) -> str:
        return self.enumerator_of(HolderStatus, holder.status_id)

    def set_holder_status(self, holder: AccountHolder, enumerator: str) -> None:
        holder.status_id = self.status_id(HolderStatus, enumerator)

    # ── tabelas de domínio ─────────────────────────────────────────────

    def status_id(self, model, enumerator: str) -> int:
        cache_key = (model.__tablename__, enumerator)
        if cache_key not in self._status_ids:
            self._status_ids[cache_key] = self.session.query(model.id).filter(model.enumerator == enumerator).scalar()
        return self._status_ids[cache_key]

    def enumerator_of(self, model, status_id: int) -> str:
        return self.session.query(model.enumerator).filter(model.id == status_id).scalar()

    def _open_status_ids(self) -> list:
        return [self.status_id(HolderStatus, enumerator) for enumerator in OPEN_HOLDER_STATUSES]

    def _new_account_number(self) -> str:
        while True:
            number = gerar_numero_da_conta()
            if self.session.query(Account.id).filter(Account.account_number == number).first() is None:
                return number
