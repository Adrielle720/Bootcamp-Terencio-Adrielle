from connectors.rest_connector import RestConnector
from constants import DOCUMENT_ANALYSIS_URL, INTERNAL_TOKEN, SERVICE_TIMEOUT


class DocumentAnalysisConnector(RestConnector):
    def __init__(self) -> None:
        super().__init__(__name__, DOCUMENT_ANALYSIS_URL, SERVICE_TIMEOUT, INTERNAL_TOKEN)

    def analyze(self, document_type: str, document_number: str, owner_document_number: str):
        payload = {
            "document_type": document_type,
            "document_number": document_number,
            "owner_document_number": owner_document_number,
        }
        return self.send("/document-analysis/analyses", "POST", payload=payload)
