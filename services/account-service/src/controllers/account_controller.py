from sqlalchemy.exc import IntegrityError

from controllers.base_controller import BaseController
from errors import (
    AccountInWrongStatus,
    AccountNotFound,
    ContactAlreadyInvited,
    CustomerAlreadyInAccount,
    CustomerNotFound,
    InvalidInvitation,
    MasterIsUnderage,
    NotMaster,
)
from dtos import account_to_dict, holder_to_dict
from repositories import AccountRepository
from utils.age import ADULT_AGE, age_in_years


class AccountController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

    def create(self, account_data: dict) -> dict:
        master, invites = self._validate_new_account(account_data)

        account = self.account_repository.create_account(account_data["name"], master.customer_key)
        self.account_repository.add_holder(account, "MASTER", "ACTIVE", customer=master)
        for invite in invites:
            self.account_repository.add_holder(account, "MEMBER", "INVITED", **invite)

        try:
            self.session.commit()
        except IntegrityError:
            # Outro grupo convidou a mesma pessoa (ou o mesmo contato) entre a
            # conferência e o commit: o índice único parcial barrou. Conferir
            # de novo, agora vendo o que o outro gravou, diz qual erro dar.
            self.session.rollback()
            self._validate_new_account(account_data)
            raise

        return {"account_key": account.account_key, "account_number": account.account_number}

    def get(self, account_key: str, customer_key: str) -> dict:
        account, _ = self._require_active_holder(account_key, customer_key)

        holders = [
            holder_to_dict(holder, customer, self.account_repository.holder_status(holder))
            for holder, customer in self.account_repository.holders_of(account)
        ]
        return account_to_dict(
            account,
            self.account_repository.account_status(account),
            self.account_repository.balance_of(account),
            holders,
        )

    def cancel(self, account_key: str, customer_key: str) -> dict:
        account = self._require_master(account_key, customer_key, required_status="PENDING")

        self.account_repository.cancel_account(account, customer_key, "Conta pendente cancelada pelo master")
        self.session.commit()

        return {"account_key": account.account_key, "status": "CANCELED"}

    def block(self, account_key: str, customer_key: str, reason: str) -> dict:
        account = self._require_master(account_key, customer_key, required_status="ACTIVE")

        self.account_repository.set_account_status(account, "BLOCKED", customer_key, reason)
        self.session.commit()

        return {"account_key": account.account_key, "status": "BLOCKED"}

    def unblock(self, account_key: str, customer_key: str) -> dict:
        account = self._require_master(account_key, customer_key, required_status="BLOCKED")

        self.account_repository.set_account_status(account, "ACTIVE", customer_key, "Conta desbloqueada pelo master")
        self.session.commit()

        return {"account_key": account.account_key, "status": "ACTIVE"}

    def set_transfer_limit(self, account_key: str, customer_key: str, limit_cents) -> dict:
        account = self._require_master(account_key, customer_key)

        account.transfer_limit_cents = limit_cents
        self.session.commit()

        return {"account_key": account.account_key, "transfer_limit_cents": limit_cents}

    def _validate_new_account(self, account_data: dict):
        master = self.account_repository.get_customer_by_key(account_data["customer_key"])
        if master is None:
            raise CustomerNotFound(account_data["customer_key"])

        age = age_in_years(master.birthdate)
        if age < ADULT_AGE:
            raise MasterIsUnderage(age, ADULT_AGE)

        if self.account_repository.has_open_holder(master):
            raise CustomerAlreadyInAccount(master.customer_key)

        invites = []
        seen_customers = {master.id}
        seen_contacts = set()
        for invite_data in account_data["invites"]:
            email, phone = invite_data.get("email"), invite_data.get("phone")
            contact = email or phone
            if contact in seen_contacts:
                raise InvalidInvitation(contact)
            seen_contacts.add(contact)

            customer = self.account_repository.get_customer_by_contact(email=email, phone=phone)
            if customer is not None:
                if customer.id in seen_customers:
                    raise InvalidInvitation(contact)
                seen_customers.add(customer.id)
                if self.account_repository.has_open_holder(customer):
                    raise CustomerAlreadyInAccount(customer.customer_key)
            elif self.account_repository.has_pending_invite_for_contact(email=email, phone=phone):
                raise ContactAlreadyInvited(contact)

            invites.append({"customer": customer, "email": email, "phone": phone})

        return master, invites

    def _require_active_holder(self, account_key: str, customer_key: str, lock: bool = False):
        """Conta inexistente e "quem pede não é titular ativo" dão o mesmo 404 (R8)."""
        account = self.account_repository.get_account_by_key(account_key, lock=lock)
        customer = self.account_repository.get_customer_by_key(customer_key)
        holder = self.account_repository.get_active_holder(account, customer)
        if holder is None:
            raise AccountNotFound(account_key)

        return account, holder

    def _require_master(self, account_key: str, customer_key: str, required_status: str = None):
        account, holder = self._require_active_holder(account_key, customer_key, lock=True)
        if holder.role != "MASTER":
            raise NotMaster(customer_key)

        if required_status is not None and self.account_repository.account_status(account) != required_status:
            raise AccountInWrongStatus(account_key)

        return account
