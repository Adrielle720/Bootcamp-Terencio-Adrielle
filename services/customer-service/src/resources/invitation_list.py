from fastapi import status
from fastapi.responses import JSONResponse

from controllers import InvitationListController


class InvitationListResource:
    def on_get(self, customer_key: str) -> JSONResponse:
        invitations = InvitationListController().list(customer_key)

        return JSONResponse(content=invitations, status_code=status.HTTP_200_OK)
