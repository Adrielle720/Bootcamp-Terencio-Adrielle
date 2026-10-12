from datetime import date

from sqlalchemy.exc import IntegrityError

from connectors import CustomerConnector, TransactionConnector
from controllers.base_controller import BaseController
from errors import (
    AccountInWrongStatus,
    AccountNotFound,
    ContactAlreadyInvited,
    CustomerAlreadyInAccount,
    CustomerNotApproved,
    CustomerNotFound,
    IdempotencyConflict,
    InvalidInvitation,
    MasterIsUnderage,
    NotMaster,
)
from dtos import account_to_dict, holder_to_dict
from repositories import AccountRepository, IdempotencyRepository
from utils.age import ADULT_AGE, age_in_years
from utils.request_hash import request_hash

IDEMPOTENCY_SCOPE = "POST /accounts"


class AccountController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.idempotency_repository = IdempotencyRepository(self.context)
        self.customer_connector = CustomerConnector()

    def create(self, account_data: dict, idempotency_key: str = None) -> dict:
        body_hash = request_hash(account_data)
        previous = self._previous_response(idempotency_key, body_hash)
        if previous is not None:
            return previous

        # Os dados de fora são lidos antes de qualquer gravação: se o
        # customer-service não responde, a resposta é 503 e nada foi gravado.
        master, invites = self._validate_new_account(account_data)

        try:
            account = self.account_repository.create_account(account_data["name"], master["customer_key"])
            self.account_repository.add_holder(account, "MASTER", "ACTIVE", customer=master,
                                               reason="Master abriu a conta")
            for invite in invites:
                self.account_repository.add_holder(account, "MEMBER", "INVITED", reason="Convite do master", **invite)
                if invite["customer"] is not None:
                    self.account_repository.notify(invite["customer"]["customer_key"], account, "INVITATION",
                                                   {"account_key": account.account_key, "account_name": account.name})

            response = {"account_key": account.account_key, "account_number": account.account_number,
                        "status": "PENDING"}
            if idempotency_key is not None:
                self.idempotency_repository.save(IDEMPOTENCY_SCOPE, idempotency_key, body_hash, 201, response)

            self.session.commit()
        except IntegrityError:
            # Outro grupo convidou a mesma pessoa (ou o mesmo contato) entre a
            # conferência e o commit: o índice único parcial barrou. Conferir
            # de novo, agora vendo o que o outro gravou, diz qual erro dar.
            self.session.rollback()
            previous = self._previous_response(idempotency_key, body_hash)
            if previous is not None:
                return previous
            self._validate_new_account(account_data)
            raise

        return response

    def get(self, account_key: str, customer_key: str) -> dict:
        account, _ = self._require_active_holder(account_key, customer_key)

        holders = [
            holder_to_dict(holder, self.account_repository.holder_role(holder),
                           self.account_repository.holder_status(holder))
            for holder in self.account_repository.holders_of(account)
        ]
        balance_cents = TransactionConnector().balance_of(account.account_key)
        return account_to_dict(account, self.account_repository.account_status(account), balance_cents, holders)

    def cancel(self, account_key: str, customer_key: str) -> dict:
        account = self._require_master(account_key, customer_key, required_status="PENDING")

        self.account_repository.cancel_account(account, customer_key, "Conta pendente cancelada pelo master")
        self.session.commit()

        return {"account_key": account.account_key, "status": "CANCELED"}

    def block(self, account_key: str, customer_key: str, reason: str) -> dict:
        account = self._require_master(account_key, customer_key, required_status="ACTIVE")

        self.account_repository.set_account_status(account, "BLOCKED", customer_key, reason)
        self.account_repository.notify_active_holders(account, "ACCOUNT_BLOCKED", {"reason": reason},
                                                      except_customer_key=customer_key)
        self.session.commit()

        return {"account_key": account.account_key, "status": "BLOCKED"}

    def unblock(self, account_key: str, customer_key: str) -> dict:
        account = self._require_master(account_key, customer_key, required_status="BLOCKED")

        self.account_repository.set_account_status(account, "ACTIVE", customer_key, "Conta desbloqueada pelo master")
        self.session.commit()

        return {"account_key": account.account_key, "status": "ACTIVE"}

    def set_transfer_limit(self, account_key: str, customer_key: str, limit_cents) -> dict:
        account = self._require_master(account_key, customer_key)

        previous_limit = account.transfer_limit_cents
        account.transfer_limit_cents = limit_cents
        self.account_repository.add_account_event(
            account, self.account_repository.account_status(account), customer_key, "Limite por transferência alterado",
            {"from": previous_limit, "to": limit_cents})
        self.session.commit()

        return {"account_key": account.account_key, "transfer_limit_cents": limit_cents}

    def _validate_new_account(self, account_data: dict):
        master = self.customer_connector.get_customer(account_data["customer_key"])
        if master is None:
            raise CustomerNotFound(account_data["customer_key"])

        age = age_in_years(date.fromisoformat(master["birth_date"]))
        if age < ADULT_AGE:
            raise MasterIsUnderage(age, ADULT_AGE)
        if master["status"] != "APPROVED":
            raise CustomerNotApproved(master["customer_key"])

        if self.account_repository.has_open_holder(master):
            raise CustomerAlreadyInAccount(master["customer_key"])

        invites = []
        seen_customers = {master["customer_key"]}
        seen_contacts = set()
        for invite_data in account_data["invites"]:
            email, phone = invite_data.get("email"), invite_data.get("phone")
            contact = email or phone
            if contact in seen_contacts:
                raise InvalidInvitation(contact)
            seen_contacts.add(contact)

            customer = self.customer_connector.find_by_contact(email=email, phone=phone)
            if customer is not None:
                if customer["customer_key"] in seen_customers:
                    raise InvalidInvitation(contact)
                seen_customers.add(customer["customer_key"])
                if self.account_repository.has_open_holder(customer):
                    raise CustomerAlreadyInAccount(customer["customer_key"])
            elif self.account_repository.has_pending_invite_for_contact(email=email, phone=phone):
                raise ContactAlreadyInvited(contact)

            invites.append({"customer": customer, "email": email, "phone": phone})

        return master, invites

    def _previous_response(self, idempotency_key: str, body_hash: str):
        if idempotency_key is None:
            return None

        record = self.idempotency_repository.get(IDEMPOTENCY_SCOPE, idempotency_key)
        if record is None:
            return None
        if record.request_hash != body_hash:
            raise IdempotencyConflict(idempotency_key)
        return record.response_body

    def _require_active_holder(self, account_key: str, customer_key: str, lock: bool = False):
        """Conta inexistente e "quem pede não é titular ativo" dão o mesmo 404 (R8)."""
        account = self.account_repository.get_account_by_key(account_key, lock=lock)
        holder = self.account_repository.get_active_holder(account, customer_key)
        if holder is None:
            raise AccountNotFound(account_key)

        return account, holder

    def _require_master(self, account_key: str, customer_key: str, required_status: str = None):
        account, holder = self._require_active_holder(account_key, customer_key, lock=True)
        if self.account_repository.holder_role(holder) != "MASTER":
            raise NotMaster(customer_key)

        if required_status is not None and self.account_repository.account_status(account) != required_status:
            raise AccountInWrongStatus(account_key)

        return account
