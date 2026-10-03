from fastapi import Body, status
from fastapi.responses import JSONResponse

from controllers import AccountCancelController
from utils.schema_handler import SchemaHandler


class AccountCancelResource:
    @SchemaHandler.validate("holder_action.json")
    def on_put(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        account = AccountCancelController().cancel(account_key, payload["customer_key"])

        return JSONResponse(content=account, status_code=status.HTTP_200_OK)
