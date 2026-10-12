from typing import Optional

from fastapi import Body, Header, status
from fastapi.responses import JSONResponse

from controllers import TransferController
from utils.schema_handler import SchemaHandler


class TransferResource:
    @SchemaHandler.validate("post_transfer.json")
    def on_post(self, account_key: str, payload: dict = Body(...),
                idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")) -> JSONResponse:
        transfer = TransferController().create(account_key, payload, idempotency_key)

        return JSONResponse(content=transfer, status_code=status.HTTP_201_CREATED)
