from datetime import datetime

from sqlalchemy.exc import IntegrityError

from controllers.base_controller import BaseController
from errors import (
    AccountInWrongStatus,
    AccountNotFound,
    ContactAlreadyInvited,
    CustomerAlreadyInAccount,
    CustomerNotFound,
    HolderIsNotMinor,
    HolderNotFound,
    HolderNotPending,
    InvalidInvitation,
    NoSeatsLeft,
    NotMaster,
)
from dtos import invitation_to_dict
from repositories import AccountRepository
from utils.age import is_adult

MAXIMUM_HOLDERS = 6
STATUSES_THAT_TAKE_NO_INVITES = ["CANCELED", "CLOSING", "CLOSED"]


class HolderController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def invite(self, account_key: str, invitation_data: dict) -> dict:
        customer_key = invitation_data["customer_key"]
        email, phone = invitation_data.get("email"), invitation_data.get("phone")
        contact = email or phone

        # A linha da conta fica travada até o commit: dois convites
        # disputando a última vaga contam um depois do outro.
        account = self.account_repository.get_account_by_key(account_key, lock=True)
        requester = self.account_repository.get_customer_by_key(customer_key)
        holder = self.account_repository.get_active_holder(account, requester)
        if holder is None:
            # Cancelar a conta solta o master (ele vira LEFT, para poder abrir
            # outra). Quem foi master dela ainda ouve o motivo real da recusa;
            # para qualquer outra pessoa, a conta segue não existindo (R8).
            if self.account_repository.was_master_of(account, requester) and \
                    self.account_repository.account_status(account) in STATUSES_THAT_TAKE_NO_INVITES:
                raise AccountInWrongStatus(account_key)
            raise AccountNotFound(account_key)
        if holder.role != "MASTER":
            raise NotMaster(customer_key)
        if self.account_repository.account_status(account) in STATUSES_THAT_TAKE_NO_INVITES:
            raise AccountInWrongStatus(account_key)
        if self.account_repository.count_seats(account) >= MAXIMUM_HOLDERS:
            raise NoSeatsLeft()

        invited = self.account_repository.get_customer_by_contact(email=email, phone=phone)
        if invited is not None:
            if invited.id == requester.id:
                raise InvalidInvitation(contact)
            if self.account_repository.has_open_holder(invited):
                raise CustomerAlreadyInAccount(invited.customer_key)
        elif self.account_repository.has_pending_invite_for_contact(email=email, phone=phone):
            raise ContactAlreadyInvited(contact)

        new_holder = self.account_repository.add_holder(account, "MEMBER", "INVITED",
                                                        customer=invited, email=email, phone=phone)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            if invited is not None:
                raise CustomerAlreadyInAccount(invited.customer_key)
            raise ContactAlreadyInvited(contact)

        return {"account_holder_key": new_holder.holder_key}

    def list_invitations(self, customer_key: str) -> dict:
        customer = self.account_repository.get_customer_by_key(customer_key)
        if customer is None:
            raise CustomerNotFound(customer_key)

        invitations = self.account_repository.pending_invitations_of(customer)
        return {"data": [invitation_to_dict(holder, account) for holder, account in invitations]}

    def accept(self, holder_key: str, customer_key: str) -> dict:
        holder, customer, account = self._find_pending_invitation(holder_key, customer_key)

        if self.account_repository.has_joined_account(customer):
            raise CustomerAlreadyInAccount(customer_key)

        # Os outros convites pendentes da pessoa caem antes de este virar
        # vínculo: o índice único não deixa dois vínculos abertos da mesma
        # customer_key existirem ao mesmo tempo.
        for other in self._other_invitations_of(customer, holder):
            self.account_repository.set_holder_status(other, "CANCELED")
            if other.account_id == account.id:
                continue
            other_account = self.account_repository.get_account_by_id(other.account_id)
            self.account_repository.cancel_if_no_invite_left(
                other_account, customer_key, "Convidado aceitou outra conta")
        self.session.flush()

        holder.customer_id = customer.id
        if is_adult(customer.birthdate):
            holder.role = "MEMBER"
            self.account_repository.set_holder_status(holder, "ACTIVE")
            holder.joined_at = datetime.now()
            if self.account_repository.account_status(account) == "PENDING":
                self.account_repository.set_account_status(account, "ACTIVE", customer_key, "Primeiro convidado aceitou")
        else:
            # O menor só fica ativo com uma guarda aprovada; até lá, ocupa a
            # vaga mas não movimenta, e não ativa a conta.
            holder.role = "MINOR"
            self.account_repository.set_holder_status(holder, "PENDING_GUARDIANSHIP")

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise CustomerAlreadyInAccount(customer_key)

        return {"account_holder_key": holder.holder_key, "status": self.account_repository.holder_status(holder)}

    def decline(self, holder_key: str, customer_key: str) -> dict:
        holder, _, account = self._find_pending_invitation(holder_key, customer_key)

        self.account_repository.set_holder_status(holder, "DECLINED")
        self.account_repository.cancel_if_no_invite_left(account, customer_key, "Último convite recusado")
        self.session.commit()

        return {"account_holder_key": holder.holder_key, "status": "DECLINED"}

    def cancel(self, holder_key: str, customer_key: str) -> dict:
        holder, account = self._find_holder_for_master(holder_key, customer_key)
        if self.account_repository.holder_status(holder) != "INVITED":
            raise HolderNotPending(holder_key)

        self.account_repository.set_holder_status(holder, "CANCELED")
        self.account_repository.cancel_if_no_invite_left(account, customer_key, "Último convite cancelado pelo master")
        self.session.commit()

        return {"account_holder_key": holder.holder_key, "status": "CANCELED"}

    def set_monthly_limit(self, holder_key: str, customer_key: str, limit_cents) -> dict:
        holder, _ = self._find_holder_for_master(holder_key, customer_key, not_holder_error=AccountNotFound)
        if holder.role != "MINOR":
            raise HolderIsNotMinor(holder_key)

        holder.monthly_limit_cents = limit_cents
        self.session.commit()

        return {"account_holder_key": holder.holder_key, "monthly_limit_cents": limit_cents}

    def _find_pending_invitation(self, holder_key: str, customer_key: str):
        """O convite é de quem pede se a customer_key bate, ou se o contato
        convidado é um dos contatos atuais da pessoa. Senão, 404."""
        holder = self.account_repository.get_holder_by_key(holder_key)
        customer = self.account_repository.get_customer_by_key(customer_key)
        if holder is None or customer is None or not self.account_repository.invitation_belongs_to(holder, customer):
            raise HolderNotFound(holder_key)

        # Trava a conta e relê o convite: dois aceites do mesmo convite ao
        # mesmo tempo passam por aqui um de cada vez.
        account = self.account_repository.get_account_by_id(holder.account_id, lock=True)
        self.session.refresh(holder)
        if self.account_repository.holder_status(holder) != "INVITED":
            raise HolderNotPending(holder_key)

        return holder, customer, account

    def _find_holder_for_master(self, holder_key: str, customer_key: str, not_holder_error=None):
        holder = self.account_repository.get_holder_by_key(holder_key)
        if holder is None:
            raise HolderNotFound(holder_key)

        account = self.account_repository.get_account_by_id(holder.account_id, lock=True)
        requester = self.account_repository.get_customer_by_key(customer_key)
        requester_holder = self.account_repository.get_active_holder(account, requester)
        if requester_holder is None:
            if not_holder_error is not None:
                raise not_holder_error(account.account_key)
            raise HolderNotFound(holder_key)
        if requester_holder.role != "MASTER":
            raise NotMaster(customer_key)

        self.session.refresh(holder)
        return holder, account

    def _other_invitations_of(self, customer, accepted_holder) -> list:
        return [
            other for other, _ in self.account_repository.pending_invitations_of(customer)
            if other.id != accepted_holder.id
        ]
