from fastapi import Body, Request, status
from fastapi.responses import JSONResponse

from controllers import HolderController
from utils.schema_handler import SchemaHandler


class AccountHolderResource:
    @SchemaHandler.validate("post_holder.json")
    def on_post(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        holder = HolderController().invite(account_key, payload)

        return JSONResponse(content=holder, status_code=status.HTTP_201_CREATED)

    @SchemaHandler.validate_query_params("get_account_holders.json")
    def on_get_list(self, request: Request) -> JSONResponse:
        invitations = HolderController().list_invitations(request.query_params["customer_key"])

        return JSONResponse(content=invitations, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("holder_action.json")
    def on_put_accept(self, account_holder_key: str, payload: dict = Body(...)) -> JSONResponse:
        holder = HolderController().accept(account_holder_key, payload["customer_key"])

        return JSONResponse(content=holder, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("holder_action.json")
    def on_put_decline(self, account_holder_key: str, payload: dict = Body(...)) -> JSONResponse:
        holder = HolderController().decline(account_holder_key, payload["customer_key"])

        return JSONResponse(content=holder, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("holder_action.json")
    def on_put_cancel(self, account_holder_key: str, payload: dict = Body(...)) -> JSONResponse:
        holder = HolderController().cancel(account_holder_key, payload["customer_key"])

        return JSONResponse(content=holder, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("set_limit.json")
    def on_put_monthly_limit(self, account_holder_key: str, payload: dict = Body(...)) -> JSONResponse:
        limit = HolderController().set_monthly_limit(account_holder_key, payload["customer_key"], payload["limit_cents"])

        return JSONResponse(content=limit, status_code=status.HTTP_200_OK)
