from controllers.base_controller import BaseController
from errors import AccountNotFound, DestinationNotFound
from repositories import AccountRepository, GuardianshipRepository
from utils.age import is_adult


class InternalController(BaseController):
    """O que os outros serviços precisam saber de uma conta, numa chamada só.

    O transaction-service e o statement-service leem isto no começo da
    operação, antes de qualquer trava do lado deles.
    """

    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.guardianship_repository = GuardianshipRepository(self.context)

    def account_context(self, account_key: str, customer_key: str) -> dict:
        account = self.account_repository.get_account_by_key(account_key)
        requester = self.account_repository.get_active_holder(account, customer_key)
        if requester is None:
            raise AccountNotFound(account_key)

        active_holders = self.account_repository.active_holders_of(account)
        if self._end_restrictions_of_new_adults(active_holders):
            self.session.commit()

        return {
            "account_key": account.account_key,
            "account_number": account.account_number,
            "status": self.account_repository.account_status(account),
            "transfer_limit_cents": account.transfer_limit_cents,
            "adult_count": sum(1 for holder in active_holders if is_adult(holder.birth_date)),
            "requester": {
                **self._holder_to_dict(requester),
                "role": self.account_repository.holder_role(requester),
                "is_minor": not is_adult(requester.birth_date),
                "monthly_limit_cents": requester.monthly_limit_cents,
            },
            "active_holders": [self._holder_to_dict(holder) for holder in active_holders],
        }

    def destination(self, account_number: str, document_number: str) -> dict:
        """Conta inexistente e CPF que não é de titular ativo dão o mesmo 404."""
        account = self.account_repository.get_account_by_number(account_number)
        if account is None:
            raise DestinationNotFound()
        verified = self.account_repository.get_active_holder_by_document(account, document_number)
        if verified is None:
            raise DestinationNotFound()

        return {
            "account_key": account.account_key,
            "account_number": account.account_number,
            "status": self.account_repository.account_status(account),
            "verified_holder": self._holder_to_dict(verified),
            "active_holders": [self._holder_to_dict(holder) for holder in self.account_repository.active_holders_of(account)],
        }

    def _end_restrictions_of_new_adults(self, active_holders: list) -> bool:
        """Ao completar 18 anos, as restrições caem sozinhas: o MINOR vira
        MEMBER e a guarda termina, com os eventos gravados."""
        changed = False
        for holder in active_holders:
            if self.account_repository.holder_role(holder) == "MINOR" and is_adult(holder.birth_date):
                self.account_repository.set_holder_role(holder, "MEMBER")
                self.account_repository.add_holder_event(holder, "Titular completou 18 anos")
                for guardianship in self.guardianship_repository.approved_guardianships_of(holder):
                    self.guardianship_repository.set_status(guardianship, "ENDED", "Menor completou 18 anos")
                changed = True
        return changed

    @staticmethod
    def _holder_to_dict(holder) -> dict:
        return {
            "account_holder_key": holder.account_holder_key,
            "customer_key": holder.customer_key,
            "name": holder.name,
        }
