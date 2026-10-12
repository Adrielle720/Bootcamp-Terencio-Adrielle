from urllib.parse import quote

import requests

from connectors.rest_connector import RestConnector
from constants import CUSTOMER_SERVICE_URL, INTERNAL_TOKEN, SERVICE_TIMEOUT
from errors import ServiceUnavailable


class CustomerConnector(RestConnector):
    """O customer-service visto daqui: quem é dono de um contato, e os dados de um cliente.

    404 é resposta válida ("não existe") e vira None. Sem resposta no prazo,
    ou resposta inesperada, vira 503: nada foi gravado, e o app pode repetir.
    """

    def __init__(self) -> None:
        super().__init__(__name__, CUSTOMER_SERVICE_URL, SERVICE_TIMEOUT, INTERNAL_TOKEN)

    def get_customer(self, customer_key: str):
        return self._get(f"/internal/customers/{customer_key}")

    def find_by_contact(self, email: str = None, phone: str = None):
        query = f"email={quote(email)}" if email is not None else f"phone={phone}"
        return self._get(f"/internal/customers?{query}")

    def get_document(self, document_key: str):
        return self._get(f"/internal/documents/{document_key}")

    def _get(self, endpoint: str):
        try:
            response = self.send(endpoint, "GET")
        except requests.RequestException:
            raise ServiceUnavailable("customer-service")

        if response.status == 404:
            return None
        if response.status != 200 or not isinstance(response.json, dict):
            raise ServiceUnavailable("customer-service")
        return response.json
