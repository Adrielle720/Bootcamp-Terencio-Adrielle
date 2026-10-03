from fastapi import Body, status
from fastapi.responses import JSONResponse

from controllers import AccountController
from utils.schema_handler import SchemaHandler


class AccountResource:
    @SchemaHandler.validate("post_account.json")
    def on_post(self, payload: dict = Body(...)) -> JSONResponse:
        account = AccountController().create(payload)

        return JSONResponse(content=account, status_code=status.HTTP_201_CREATED)
