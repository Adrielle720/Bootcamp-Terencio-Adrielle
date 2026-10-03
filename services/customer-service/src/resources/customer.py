from fastapi import Request, status
from fastapi.responses import JSONResponse

from controllers import CustomerController


class CustomerResource:
    async def on_post(self, request: Request) -> JSONResponse:
        customer_data = await request.json()

        customer_key = CustomerController().create(customer_data)

        return JSONResponse(content=customer_key, status_code=status.HTTP_201_CREATED)
