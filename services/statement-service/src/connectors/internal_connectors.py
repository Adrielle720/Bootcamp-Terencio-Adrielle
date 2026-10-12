from urllib.parse import urlencode

import requests

from connectors.rest_connector import RestConnector
from constants import ACCOUNT_SERVICE_URL, INTERNAL_TOKEN, SERVICE_TIMEOUT, TRANSACTION_SERVICE_URL
from errors import InvalidSchema, ServiceUnavailable


class _InternalConnector(RestConnector):
    """Leitura de outro serviço: 404 vira None, 400 volta como 400, o resto é 503."""

    service_name = ""

    def _get(self, endpoint: str):
        try:
            response = self.send(endpoint, "GET")
        except requests.RequestException:
            raise ServiceUnavailable(self.service_name)

        if response.status == 404:
            return None
        if response.status == 400 and isinstance(response.json, dict):
            raise InvalidSchema(response.json.get("description", "invalid parameter"))
        if response.status != 200 or not isinstance(response.json, dict):
            raise ServiceUnavailable(self.service_name)
        return response.json


class AccountConnector(_InternalConnector):
    service_name = "account-service"

    def __init__(self) -> None:
        super().__init__(__name__, ACCOUNT_SERVICE_URL, SERVICE_TIMEOUT, INTERNAL_TOKEN)

    def context(self, account_key: str, customer_key: str):
        return self._get(f"/internal/accounts/{account_key}/context?{urlencode({'customer_key': customer_key})}")


class TransactionConnector(_InternalConnector):
    service_name = "transaction-service"

    def __init__(self) -> None:
        super().__init__(__name__, TRANSACTION_SERVICE_URL, SERVICE_TIMEOUT, INTERNAL_TOKEN)

    def entries(self, account_key: str, filters: dict):
        query = urlencode({name: value for name, value in filters.items() if value is not None})
        return self._get(f"/internal/accounts/{account_key}/entries?{query}")

    def transaction(self, account_key: str, transaction_key: str):
        return self._get(f"/internal/accounts/{account_key}/transactions/{transaction_key}")
