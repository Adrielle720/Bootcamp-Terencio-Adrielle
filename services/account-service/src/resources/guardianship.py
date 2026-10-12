from fastapi import Body, Request, status
from fastapi.responses import JSONResponse

from controllers import GuardianshipController
from utils.schema_handler import SchemaHandler


class GuardianshipResource:
    @SchemaHandler.validate("post_guardianship.json")
    def on_post(self, account_key: str, payload: dict = Body(...)) -> JSONResponse:
        guardianship = GuardianshipController().create(account_key, payload)

        return JSONResponse(content=guardianship, status_code=status.HTTP_201_CREATED)

    @SchemaHandler.validate_query_params("get_account.json")
    def on_get(self, guardianship_key: str, request: Request) -> JSONResponse:
        guardianship = GuardianshipController().get(guardianship_key, request.query_params["customer_key"])

        return JSONResponse(content=guardianship, status_code=status.HTTP_200_OK)
