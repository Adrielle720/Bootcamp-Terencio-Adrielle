from typing import Optional

from fastapi import Body, Header, Request, status
from fastapi.responses import JSONResponse

from controllers import AccountController
from utils.schema_handler import SchemaHandler


class AccountResource:
    @SchemaHandler.validate("post_account.json")
    def on_post(self, payload: dict = Body(...),
                idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")) -> JSONResponse:
        account = AccountController().create(payload, idempotency_key)

        return JSONResponse(content=account, status_code=status.HTTP_201_CREATED)

    @SchemaHandler.validate_query_params("get_account.json")
    def on_get(self, account_key: str, request: Request) -> JSONResponse:
        account = AccountController().get(account_key, request.query_params["customer_key"])

        return JSONResponse(content=account, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("holder_action.json")
    def on_put_cancel(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        account = AccountController().cancel(account_key, payload["customer_key"])

        return JSONResponse(content=account, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("block_account.json")
    def on_put_block(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        account = AccountController().block(account_key, payload["customer_key"], payload["reason"])

        return JSONResponse(content=account, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("holder_action.json")
    def on_put_unblock(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        account = AccountController().unblock(account_key, payload["customer_key"])

        return JSONResponse(content=account, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("set_limit.json")
    def on_put_transfer_limit(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        limit = AccountController().set_transfer_limit(account_key, payload["customer_key"], payload["limit_cents"])

        return JSONResponse(content=limit, status_code=status.HTTP_200_OK)
