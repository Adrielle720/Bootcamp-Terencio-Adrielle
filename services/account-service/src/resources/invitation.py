from fastapi import Body, status
from fastapi.responses import JSONResponse

from controllers import InvitationController
from utils.schema_handler import SchemaHandler


class InvitationResource:
    @SchemaHandler.validate("post_invitation.json")
    def on_post(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        holder = InvitationController().create(account_key, payload)

        return JSONResponse(content=holder, status_code=status.HTTP_201_CREATED)
