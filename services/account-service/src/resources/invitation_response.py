from fastapi import Body, status
from fastapi.responses import JSONResponse

from controllers import InvitationCancelController, InvitationResponseController
from utils.schema_handler import SchemaHandler


class InvitationResponseResource:
    @SchemaHandler.validate("holder_action.json")
    def on_put_accept(self, holder_key: str, payload: dict = Body(...)) -> JSONResponse:
        holder = InvitationResponseController().accept(holder_key, payload["customer_key"])

        return JSONResponse(content=holder, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("holder_action.json")
    def on_put_decline(self, holder_key: str, payload: dict = Body(...)) -> JSONResponse:
        holder = InvitationResponseController().decline(holder_key, payload["customer_key"])

        return JSONResponse(content=holder, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("holder_action.json")
    def on_put_cancel(self, holder_key: str, payload: dict = Body(...)) -> JSONResponse:
        holder = InvitationCancelController().cancel(holder_key, payload["customer_key"])

        return JSONResponse(content=holder, status_code=status.HTTP_200_OK)
