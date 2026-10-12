from connectors import AccountConnector, TransactionConnector
from controllers.base_controller import BaseController
from errors import AccountNotFound, ServiceUnavailable, TransactionNotFound

# holder_key que não é titular ativo desta conta: o filtro não casa com nada,
# em vez de dizer a quem pergunta se aquela chave existe em outro lugar.
NOBODY = "00000000-0000-0000-0000-000000000000"
PASSED_FILTERS = ["limit", "page", "start_date", "end_date", "type", "direction"]


class StatementController(BaseController):
    """O extrato é composição de API: quem pode ver vem do account-service,
    o que aconteceu vem do transaction-service. Nada é guardado aqui."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_connector = AccountConnector()
        self.transaction_connector = TransactionConnector()

    def list(self, account_key: str, query: dict) -> dict:
        context = self._require_active_holder(account_key, query["customer_key"])

        filters = {name: query.get(name) for name in PASSED_FILTERS}
        holder_key = query.get("holder_key")
        if holder_key is not None:
            filters["made_by"] = next(
                (holder["customer_key"] for holder in context["active_holders"]
                 if holder["account_holder_key"] == holder_key),
                NOBODY,
            )

        statement = self.transaction_connector.entries(account_key, filters)
        if statement is None:
            raise ServiceUnavailable("transaction-service")

        return {**statement, "data": [self._public(item) for item in statement["data"]]}

    def get(self, account_key: str, transaction_key: str, customer_key: str) -> dict:
        self._require_active_holder(account_key, customer_key)

        transaction = self.transaction_connector.transaction(account_key, transaction_key)
        if transaction is None:
            raise TransactionNotFound(transaction_key)

        return self._public(transaction)

    def _require_active_holder(self, account_key: str, customer_key: str) -> dict:
        """Conta inexistente e quem pede não ser titular ativo dão o mesmo 404 (R8).
        Quem saiu da conta perde o acesso ao extrato."""
        context = self.account_connector.context(account_key, customer_key)
        if context is None:
            raise AccountNotFound(account_key)
        return context

    @staticmethod
    def _public(item: dict) -> dict:
        """A customer_key de quem fez a operação serve ao filtro, mas não sai na resposta."""
        return {**item, "made_by": {"name": item["made_by"]["name"]}}
