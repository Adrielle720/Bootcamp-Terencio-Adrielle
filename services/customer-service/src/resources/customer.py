from typing import Optional

from fastapi import Body, Header, Request, status
from fastapi.responses import JSONResponse

from controllers import CustomerController, DocumentController
from utils.schema_handler import SchemaHandler


class CustomerResource:
    @SchemaHandler.validate("post_customer.json")
    def on_post(self, payload: dict = Body(...),
                idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")) -> JSONResponse:
        customer = CustomerController().create(payload, idempotency_key)

        return JSONResponse(content=customer, status_code=status.HTTP_201_CREATED)

    def on_get(self, customer_key: str) -> JSONResponse:
        customer = CustomerController().get(customer_key)

        return JSONResponse(content=customer, status_code=status.HTTP_200_OK)

    @SchemaHandler.validate("post_document.json")
    def on_post_document(self, customer_key: str, payload: dict = Body(...)) -> JSONResponse:
        document = DocumentController().create(customer_key, payload)

        return JSONResponse(content=document, status_code=status.HTTP_201_CREATED)

    def on_get_documents(self, customer_key: str) -> JSONResponse:
        documents = DocumentController().list(customer_key)

        return JSONResponse(content=documents, status_code=status.HTTP_200_OK)


class InternalCustomerResource:
    """Rotas só entre serviços: o account-service pergunta quem é dono de um contato e os dados de um cliente."""

    @SchemaHandler.validate_query_params("get_internal_customers.json")
    def on_get_by_contact(self, request: Request) -> JSONResponse:
        customer = CustomerController().find_by_contact(request.query_params.get("email"),
                                                        request.query_params.get("phone"))

        return JSONResponse(content=customer, status_code=status.HTTP_200_OK)

    def on_get(self, customer_key: str) -> JSONResponse:
        customer = CustomerController().get_internal(customer_key)

        return JSONResponse(content=customer, status_code=status.HTTP_200_OK)

    def on_get_document(self, document_key: str) -> JSONResponse:
        document = DocumentController().get_internal(document_key)

        return JSONResponse(content=document, status_code=status.HTTP_200_OK)
