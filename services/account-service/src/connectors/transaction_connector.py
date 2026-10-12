import requests

from connectors.rest_connector import RestConnector
from constants import INTERNAL_TOKEN, SERVICE_TIMEOUT, TRANSACTION_SERVICE_URL
from errors import ServiceUnavailable


class TransactionConnector(RestConnector):
    def __init__(self) -> None:
        super().__init__(__name__, TRANSACTION_SERVICE_URL, SERVICE_TIMEOUT, INTERNAL_TOKEN)

    def balance_of(self, account_key: str) -> int:
        """O saldo mora no transaction-service. Conta que nunca movimentou tem saldo zero."""
        try:
            response = self.send(f"/internal/accounts/{account_key}/entries?limit=1", "GET")
        except requests.RequestException:
            raise ServiceUnavailable("transaction-service")

        if response.status != 200 or not isinstance(response.json, dict):
            raise ServiceUnavailable("transaction-service")
        return response.json["summary"]["balance_cents"]
