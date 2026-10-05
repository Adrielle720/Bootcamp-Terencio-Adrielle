from fastapi import Body, status
from fastapi.responses import JSONResponse

from controllers import TransferLimitController
from utils.schema_handler import SchemaHandler


class TransferLimitResource:
    @SchemaHandler.validate("set_transfer_limit.json")
    def on_put(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        limit = TransferLimitController().set(account_key, payload["customer_key"], payload["limit_cents"])

        return JSONResponse(content=limit, status_code=status.HTTP_200_OK)
