from fastapi import Request, status
from fastapi.responses import JSONResponse

from controllers import StatementController
from utils.schema_handler import SchemaHandler


class StatementResource:
    @SchemaHandler.validate_query_params("get_transactions.json")
    def on_get_list(self, account_key: str, request: Request) -> JSONResponse:
        statement = StatementController().list(account_key, dict(request.query_params))

        return JSONResponse(content=statement, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate_query_params("get_transaction.json")
    def on_get_by_key(self, account_key: str, transaction_key: str, request: Request) -> JSONResponse:
        transaction = StatementController().get(account_key, transaction_key, request.query_params["customer_key"])

        return JSONResponse(content=transaction, status_code=status.HTTP_200_OK)
