from datetime import date

from controllers.base_controller import BaseController
from dtos import item_to_dict
from errors import AccountNotFound, InvalidSchema, TransactionNotFound
from repositories import StatementRepository

# holder_key que não é titular desta conta: o filtro não casa com nada,
# em vez de dizer a quem pergunta se aquela chave existe em outro lugar.
NOBODY = -1


class StatementController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.statement_repository = StatementRepository(self.context)

    def list(self, account_key: str, query: dict) -> dict:
        account = self._require_active_holder(account_key, query["customer_key"])

        limit = int(query.get("limit", 10))
        page = int(query.get("page", 0))
        filters = {
            "type": query.get("type"),
            "direction": query.get("direction"),
            "start_date": self._parse_date(query.get("start_date")),
            "end_date": self._parse_date(query.get("end_date")),
            "made_by_id": self._made_by_filter(account, query.get("holder_key")),
        }

        rows = self.statement_repository.list_items(account, filters, limit, page * limit)
        summary = self.statement_repository.summarize(account, filters)

        return {
            "summary": {"balance_cents": self.statement_repository.balance_of(account), **summary},
            "data": [item_to_dict(row) for row in rows[:limit]],
            "limit": limit,
            "page": page,
            "is_last_page": len(rows) <= limit,
        }

    def get(self, account_key: str, transaction_key: str, customer_key: str) -> dict:
        account = self._require_active_holder(account_key, customer_key)

        row = self.statement_repository.get_item(account, transaction_key)
        if row is None:
            raise TransactionNotFound(transaction_key)

        return {**item_to_dict(row), "entries": self.statement_repository.entries_of(account, transaction_key)}

    def _require_active_holder(self, account_key: str, customer_key: str):
        """Conta inexistente e quem pede não ser titular ativo dão o mesmo 404 (R8).
        Quem saiu da conta perde o acesso ao extrato."""
        account = self.statement_repository.get_customer_account_by_key(account_key)
        if not self.statement_repository.is_active_holder(account, customer_key):
            raise AccountNotFound(account_key)

        return account

    def _made_by_filter(self, account, holder_key: str):
        if holder_key is None:
            return None

        customer_id = self.statement_repository.customer_id_of_holder(account, holder_key)
        return customer_id if customer_id is not None else NOBODY

    @staticmethod
    def _parse_date(value: str):
        # O schema garantiu o formato; quem sabe que fevereiro não tem dia 30 é esta linha.
        if value is None:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise InvalidSchema(f"'{value}' is not a valid date")
