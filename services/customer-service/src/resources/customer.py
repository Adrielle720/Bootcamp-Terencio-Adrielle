from fastapi import Body, status
from fastapi.responses import JSONResponse

from controllers import CustomerController
from utils.schema_handler import SchemaHandler


class CustomerResource:
    @SchemaHandler.validate("post_customer.json")
    def on_post(self, payload: dict = Body(...)) -> JSONResponse:
        customer_key = CustomerController().create(payload)

        return JSONResponse(content=customer_key, status_code=status.HTTP_201_CREATED)
