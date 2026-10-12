from fastapi import Request, status
from fastapi.responses import JSONResponse

from controllers import InternalController
from utils.schema_handler import SchemaHandler


class InternalTransactionResource:
    """Rotas só entre serviços, com INTERNAL-TOKEN, e só de leitura."""

    @SchemaHandler.validate_query_params("get_entries.json")
    def on_get_entries(self, account_key: str, request: Request) -> JSONResponse:
        entries = InternalController().entries(account_key, dict(request.query_params))

        return JSONResponse(content=entries, status_code=status.HTTP_200_OK)

    def on_get_transaction(self, account_key: str, transaction_key: str) -> JSONResponse:
        transaction = InternalController().transaction(account_key, transaction_key)

        return JSONResponse(content=transaction, status_code=status.HTTP_200_OK)

    def on_get_institution_balances(self) -> JSONResponse:
        balances = InternalController().institution_balances()

        return JSONResponse(content=balances, status_code=status.HTTP_200_OK)
