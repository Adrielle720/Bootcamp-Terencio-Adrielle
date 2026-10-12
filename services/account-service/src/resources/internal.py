from fastapi import Request, status
from fastapi.responses import JSONResponse

from controllers import InternalController
from utils.schema_handler import SchemaHandler


class InternalAccountResource:
    """Rotas só entre serviços, com INTERNAL-TOKEN."""

    @SchemaHandler.validate_query_params("get_account.json")
    def on_get_context(self, account_key: str, request: Request) -> JSONResponse:
        context = InternalController().account_context(account_key, request.query_params["customer_key"])

        return JSONResponse(content=context, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate_query_params("get_internal_accounts.json")
    def on_get_destination(self, request: Request) -> JSONResponse:
        destination = InternalController().destination(request.query_params["number"],
                                                       request.query_params["document_number"])

        return JSONResponse(content=destination, status_code=status.HTTP_200_OK)
