from datetime import date

from controllers.base_controller import BaseController
from errors import InvalidSchema, TransactionNotFound
from repositories import StatementRepository, TransactionRepository


class InternalController(BaseController):
    """Leituras só entre serviços: o extrato monta a resposta a partir daqui.

    Quem confere se quem pede é titular ativo é o statement-service, antes de
    chamar; esta camada só sabe de dinheiro.
    """

    def __init__(self) -> None:
        super().__init__(__name__)
        self.statement_repository = StatementRepository(self.context)
        self.transaction_repository = TransactionRepository(self.context)

    def entries(self, account_key: str, query: dict) -> dict:
        limit = int(query.get("limit", 10))
        page = int(query.get("page", 0))
        start_date = self._parse_date(query.get("start_date"))
        end_date = self._parse_date(query.get("end_date"))
        if start_date is not None and end_date is not None and start_date > end_date:
            raise InvalidSchema("start_date must not be after end_date")

        filters = {
            "type": query.get("type"),
            "direction": query.get("direction"),
            "start_date": start_date,
            "end_date": end_date,
            "made_by": query.get("made_by"),
        }
        rows = self.statement_repository.list_items(account_key, filters, limit, page * limit)
        summary = self.statement_repository.summarize(account_key, filters)

        return {
            "summary": {"balance_cents": self.transaction_repository.get_balance(account_key), **summary},
            "data": [self._item(row) for row in rows[:limit]],
            "limit": limit,
            "page": page,
            "is_last_page": len(rows) <= limit,
        }

    def transaction(self, account_key: str, transaction_key: str) -> dict:
        row = self.statement_repository.get_item(account_key, transaction_key)
        if row is None:
            raise TransactionNotFound(transaction_key)

        return {**self._item(row), "entries": self.statement_repository.entries_of(account_key, transaction_key)}

    def institution_balances(self) -> dict:
        return self.transaction_repository.institution_balances()

    @staticmethod
    def _item(row: dict) -> dict:
        counterparty = None
        if row["counterparty_account_number"] is not None:
            counterparty = {"account_number": row["counterparty_account_number"], "name": row["counterparty_name"]}

        return {
            "transaction_key": row["transaction_key"],
            "type": row["type"],
            "direction": row["direction"],
            "amount_cents": row["amount_cents"],
            "fee_cents": row["fee_cents"],
            "total_cents": row["amount_cents"] + row["fee_cents"],
            "created_at": row["created_at"].isoformat(),
            "made_by": {"name": row["made_by_name"], "customer_key": row["made_by_customer_key"]},
            "counterparty": counterparty,
        }

    @staticmethod
    def _parse_date(value: str):
        # O schema garantiu o formato; quem sabe que fevereiro não tem dia 30 é esta linha.
        if value is None:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise InvalidSchema(f"'{value}' is not a valid date")
