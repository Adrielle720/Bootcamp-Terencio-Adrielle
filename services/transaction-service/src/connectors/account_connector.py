from urllib.parse import urlencode

import requests

from connectors.rest_connector import RestConnector
from constants import ACCOUNT_SERVICE_URL, INTERNAL_TOKEN, SERVICE_TIMEOUT
from errors import ServiceUnavailable


class AccountConnector(RestConnector):
    """O account-service visto daqui: o contexto da origem e a resolução do destino.

    É lido no começo da operação, antes de qualquer trava. 404 é resposta
    válida e vira None; sem resposta no prazo vira 503, e nada foi gravado.
    """

    def __init__(self) -> None:
        super().__init__(__name__, ACCOUNT_SERVICE_URL, SERVICE_TIMEOUT, INTERNAL_TOKEN)

    def context(self, account_key: str, customer_key: str):
        return self._get(f"/internal/accounts/{account_key}/context?{urlencode({'customer_key': customer_key})}")

    def destination(self, account_number: str, document_number: str):
        query = urlencode({"number": account_number, "document_number": document_number})
        return self._get(f"/internal/accounts?{query}")

    def _get(self, endpoint: str):
        try:
            response = self.send(endpoint, "GET")
        except requests.RequestException:
            raise ServiceUnavailable("account-service")

        if response.status in (400, 404):
            return None
        if response.status != 200 or not isinstance(response.json, dict):
            raise ServiceUnavailable("account-service")
        return response.json
