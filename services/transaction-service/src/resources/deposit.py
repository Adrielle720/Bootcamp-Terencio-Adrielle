from typing import Optional

from fastapi import Body, Header, status
from fastapi.responses import JSONResponse

from controllers import DepositController
from utils.schema_handler import SchemaHandler


class DepositResource:
    @SchemaHandler.validate("post_deposit.json")
    def on_post(self, account_key: str, payload: dict = Body(...),
                idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")) -> JSONResponse:
        deposit = DepositController().create(account_key, payload, idempotency_key)

        return JSONResponse(content=deposit, status_code=status.HTTP_201_CREATED)
