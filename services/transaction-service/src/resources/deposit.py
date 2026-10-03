from fastapi import Body, status
from fastapi.responses import JSONResponse

from controllers import DepositController
from utils.schema_handler import SchemaHandler


class DepositResource:
    @SchemaHandler.validate("post_deposit.json")
    def on_post(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        deposit = DepositController().create(account_key, payload)

        return JSONResponse(content=deposit, status_code=status.HTTP_201_CREATED)
