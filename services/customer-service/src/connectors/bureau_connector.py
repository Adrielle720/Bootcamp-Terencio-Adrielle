from connectors.rest_connector import RestConnector
from constants import BUREAU_TIMEOUT, BUREAU_URL, INTERNAL_TOKEN


class BureauConnector(RestConnector):
    def __init__(self) -> None:
        super().__init__(__name__, BUREAU_URL, BUREAU_TIMEOUT, INTERNAL_TOKEN)

    def consult(self, document_number: str):
        digitos = "".join(caractere for caractere in document_number if caractere.isdigit())
        return self.send(f"/bureau/cpf/{digitos}", "GET")
