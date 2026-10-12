from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import and_, or_

from database import Context
from models import (
    Account,
    AccountEvent,
    AccountHolder,
    AccountHolderEvent,
    AccountStatus,
    HolderRole,
    HolderStatus,
    Notification,
    NotificationType,
)
from utils.account_number import gerar_numero_da_conta

# Vínculos que ocupam vaga e prendem a pessoa a esta conta.
OPEN_HOLDER_STATUSES = ["INVITED", "PENDING_GUARDIANSHIP", "ACTIVE"]


class AccountRepository:
    """Única porta do banco do account-service.

    Clientes moram no customer-service: aqui eles chegam como o dicionário
    que a rota interna de lá devolve (customer_key, contatos atuais, nome,
    CPF, nascimento) e são guardados só pela customer_key.
    """

    def __init__(self, context: Context) -> None:
        self.session = context.db_session
        self._ids = {}

    # ── contas ─────────────────────────────────────────────────────────

    def get_account_by_key(self, account_key: str, lock: bool = False) -> Account:
        query = self.session.query(Account).filter(Account.account_key == account_key)
        if lock:
            query = query.with_for_update()
        return query.first()

    def get_account_by_number(self, account_number: str) -> Account:
        return self.session.query(Account).filter(Account.account_number == account_number).first()

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
        account.account_status_id = self.domain_id(AccountStatus, "PENDING")
        self.session.add(account)
        self.session.flush()

        self.add_account_event(account, "PENDING", actor_customer_key, "Conta aberta pelo master")
        return account

    def account_status(self, account: Account) -> str:
        return self.enumerator_of(AccountStatus, account.account_status_id)

    def set_account_status(self, account: Account, enumerator: str, actor_customer_key: str, reason: str,
                           payload: dict = None) -> None:
        account.account_status_id = self.domain_id(AccountStatus, enumerator)
        self.add_account_event(account, enumerator, actor_customer_key, reason, payload)

    def add_account_event(self, account: Account, enumerator: str, actor_customer_key: str, reason: str,
                          payload: dict = None) -> None:
        event = AccountEvent()
        event.account_id = account.id
        event.account_status_id = self.domain_id(AccountStatus, enumerator)
        event.actor_customer_key = actor_customer_key
        event.reason = reason
        event.payload = payload
        self.session.add(event)

    def cancel_account(self, account: Account, actor_customer_key: str, reason: str) -> None:
        """Cancela a conta e solta todo mundo que estava preso a ela.

        Convite pendente vira CANCELED; quem já estava dentro (o master, um
        menor esperando a guarda) vira LEFT. Sem isso, o índice único de
        uma conta por pessoa não deixaria o master abrir outra.
        """
        for holder in self.open_holders_of(account):
            if self.holder_status(holder) == "INVITED":
                self.set_holder_status(holder, "CANCELED", reason)
            else:
                holder.left_at = datetime.now()
                self.set_holder_status(holder, "LEFT", reason)

        self.set_account_status(account, "CANCELED", actor_customer_key, reason)

    def cancel_if_no_invite_left(self, account: Account, actor_customer_key: str, reason: str) -> None:
        self.session.flush()
        if self.account_status(account) == "PENDING" and not self.has_invited_holders(account):
            self.cancel_account(account, actor_customer_key, reason)

    # ── titulares e convites ───────────────────────────────────────────

    def get_holder_by_key(self, holder_key: str) -> AccountHolder:
        return self.session.query(AccountHolder).filter(AccountHolder.account_holder_key == holder_key).first()

    def get_holder_by_id(self, holder_id: int) -> AccountHolder:
        return self.session.query(AccountHolder).filter(AccountHolder.id == holder_id).first()

    def get_active_holder(self, account: Account, customer_key: str) -> AccountHolder:
        if account is None or customer_key is None:
            return None
        return self.session.query(AccountHolder).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.customer_key == customer_key,
            AccountHolder.holder_status_id == self.domain_id(HolderStatus, "ACTIVE"),
        ).first()

    def get_active_holder_by_document(self, account: Account, document_number: str) -> AccountHolder:
        return self.session.query(AccountHolder).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.document_number == document_number,
            AccountHolder.holder_status_id == self.domain_id(HolderStatus, "ACTIVE"),
        ).first()

    def was_master_of(self, account: Account, customer_key: str) -> bool:
        if account is None:
            return False
        return self.session.query(AccountHolder.id).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.customer_key == customer_key,
            AccountHolder.holder_role_id == self.domain_id(HolderRole, "MASTER"),
        ).first() is not None

    def holders_of(self, account: Account) -> list:
        return self.session.query(AccountHolder).filter(AccountHolder.account_id == account.id).order_by(AccountHolder.id).all()

    def active_holders_of(self, account: Account) -> list:
        return self.session.query(AccountHolder).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.holder_status_id == self.domain_id(HolderStatus, "ACTIVE"),
        ).order_by(AccountHolder.id).all()

    def open_holders_of(self, account: Account) -> list:
        return self.session.query(AccountHolder).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.holder_status_id.in_(self._open_status_ids()),
        ).all()

    def count_seats(self, account: Account) -> int:
        return len(self.open_holders_of(account))

    def has_invited_holders(self, account: Account) -> bool:
        return self.session.query(AccountHolder.id).filter(
            AccountHolder.account_id == account.id,
            AccountHolder.holder_status_id == self.domain_id(HolderStatus, "INVITED"),
        ).first() is not None

    def has_open_holder(self, customer: dict) -> bool:
        """A pessoa já está presa a alguma conta: dentro dela, ou convidada.

        O convite pode estar ligado à customer_key ou, se foi feito antes
        do cadastro, só ao e-mail ou celular que ela usa hoje.
        """
        by_customer = self.session.query(AccountHolder.id).filter(
            AccountHolder.customer_key == customer["customer_key"],
            AccountHolder.holder_status_id.in_(self._open_status_ids()),
        ).first()
        return by_customer is not None or len(self.contact_invitations_of(customer)) > 0

    def has_joined_account(self, customer_key: str) -> bool:
        return self.session.query(AccountHolder.id).filter(
            AccountHolder.customer_key == customer_key,
            AccountHolder.holder_status_id.in_([
                self.domain_id(HolderStatus, "ACTIVE"),
                self.domain_id(HolderStatus, "PENDING_GUARDIANSHIP"),
            ]),
        ).first() is not None

    def has_pending_invite_for_contact(self, email: str = None, phone: str = None) -> bool:
        contact_filter = AccountHolder.invited_email == email if email is not None else AccountHolder.invited_phone == phone
        return self.session.query(AccountHolder.id).filter(
            AccountHolder.customer_key.is_(None),
            AccountHolder.holder_status_id == self.domain_id(HolderStatus, "INVITED"),
            contact_filter,
        ).first() is not None

    def contact_invitations_of(self, customer: dict) -> list:
        return self.session.query(AccountHolder).filter(
            AccountHolder.customer_key.is_(None),
            AccountHolder.holder_status_id == self.domain_id(HolderStatus, "INVITED"),
            or_(AccountHolder.invited_email == customer["email"], AccountHolder.invited_phone == customer["phone"]),
        ).all()

    def pending_invitations_of(self, customer: dict) -> list:
        return (
            self.session.query(AccountHolder, Account)
            .join(Account, AccountHolder.account_id == Account.id)
            .filter(
                AccountHolder.holder_status_id == self.domain_id(HolderStatus, "INVITED"),
                or_(
                    AccountHolder.customer_key == customer["customer_key"],
                    and_(
                        AccountHolder.customer_key.is_(None),
                        or_(AccountHolder.invited_email == customer["email"],
                            AccountHolder.invited_phone == customer["phone"]),
                    ),
                ),
            )
            .order_by(AccountHolder.invited_at.desc())
            .all()
        )

    @staticmethod
    def invitation_belongs_to(holder: AccountHolder, customer: dict) -> bool:
        if holder.customer_key is not None:
            return holder.customer_key == customer["customer_key"]
        return holder.invited_email == customer["email"] or holder.invited_phone == customer["phone"]

    def add_holder(self, account: Account, role: str, status: str, customer: dict = None,
                   email: str = None, phone: str = None, reason: str = None) -> AccountHolder:
        holder = AccountHolder()
        holder.account_holder_key = str(uuid4())
        holder.account_id = account.id
        holder.customer_key = customer["customer_key"] if customer is not None else None
        holder.holder_role_id = self.domain_id(HolderRole, role)
        holder.holder_status_id = self.domain_id(HolderStatus, status)
        holder.invited_email = email
        holder.invited_phone = phone
        if status == "ACTIVE":
            self.copy_customer_data(holder, customer)
            holder.joined_at = datetime.now()
        self.session.add(holder)
        self.session.flush()

        self.add_holder_event(holder, reason or "Vínculo criado", {"invited_email": email, "invited_phone": phone})
        return holder

    @staticmethod
    def copy_customer_data(holder: AccountHolder, customer: dict) -> None:
        """Nome, CPF e nascimento nunca mudam depois do cadastro: copiá-los
        evita uma chamada ao customer-service sem risco de dado desatualizado."""
        holder.customer_key = customer["customer_key"]
        holder.name = customer["name"]
        holder.document_number = customer["document_number"]
        holder.birth_date = date.fromisoformat(customer["birth_date"])

    def holder_status(self, holder: AccountHolder) -> str:
        return self.enumerator_of(HolderStatus, holder.holder_status_id)

    def holder_role(self, holder: AccountHolder) -> str:
        return self.enumerator_of(HolderRole, holder.holder_role_id)

    def set_holder_status(self, holder: AccountHolder, enumerator: str, reason: str, payload: dict = None) -> None:
        holder.holder_status_id = self.domain_id(HolderStatus, enumerator)
        self.add_holder_event(holder, reason, payload)

    def set_holder_role(self, holder: AccountHolder, enumerator: str) -> None:
        holder.holder_role_id = self.domain_id(HolderRole, enumerator)

    def add_holder_event(self, holder: AccountHolder, reason: str, payload: dict = None) -> None:
        event = AccountHolderEvent()
        event.account_holder_id = holder.id
        event.holder_status_id = holder.holder_status_id
        event.holder_role_id = holder.holder_role_id
        event.reason = reason
        event.payload = payload
        self.session.add(event)

    # ── notificações ───────────────────────────────────────────────────

    def notify(self, customer_key: str, account: Account, notification_type: str, payload: dict) -> None:
        """Notificação só dentro do app: uma linha gravada no mesmo commit da operação."""
        notification = Notification()
        notification.notification_key = str(uuid4())
        notification.customer_key = customer_key
        notification.account_id = account.id
        notification.notification_type_id = self.domain_id(NotificationType, notification_type)
        notification.payload = payload
        self.session.add(notification)

    def notify_active_holders(self, account: Account, notification_type: str, payload: dict,
                              except_customer_key: str = None) -> None:
        for holder in self.active_holders_of(account):
            if holder.customer_key != except_customer_key:
                self.notify(holder.customer_key, account, notification_type, payload)

    # ── tabelas de domínio ─────────────────────────────────────────────

    def domain_id(self, model, enumerator: str) -> int:
        cache_key = (model.__tablename__, enumerator)
        if cache_key not in self._ids:
            self._ids[cache_key] = self.session.query(model.id).filter(model.enumerator == enumerator).scalar()
        return self._ids[cache_key]

    def enumerator_of(self, model, domain_id: int) -> str:
        return self.session.query(model.enumerator).filter(model.id == domain_id).scalar()

    def _open_status_ids(self) -> list:
        return [self.domain_id(HolderStatus, enumerator) for enumerator in OPEN_HOLDER_STATUSES]

    def _new_account_number(self) -> str:
        while True:
            number = gerar_numero_da_conta()
            if self.get_account_by_number(number) is None:
                return number
