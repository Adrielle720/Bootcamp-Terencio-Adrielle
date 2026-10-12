from connectors.rest_connector import RestConnector
from constants import BUREAU_URL, INTERNAL_TOKEN, SERVICE_TIMEOUT


class BureauConnector(RestConnector):
    def __init__(self) -> None:
        super().__init__(__name__, BUREAU_URL, SERVICE_TIMEOUT, INTERNAL_TOKEN)

    def consult(self, document_number: str):
        digits = "".join(character for character in document_number if character.isdigit())
        return self.send(f"/bureau/cpf/{digits}", "GET")
