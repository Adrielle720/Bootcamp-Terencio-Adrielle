from fastapi import FastAPI

from constants import check_variables
from errors import register_error_handlers
from errors.base_error import error_verification
from middlewares import (
    register_internal_token_middleware,
    register_request_context_middleware,
    register_request_logger_middleware,
    register_session_manager_middleware,
)
from resources import CustomerResource, HealthCheckResource, InternalCustomerResource
from utils.logger import setup_logging


def create_app() -> FastAPI:
    application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    register_session_manager_middleware(application)
    register_internal_token_middleware(application)
    register_request_logger_middleware(application)
    register_request_context_middleware(application)

    health_check_resource = HealthCheckResource()
    application.add_api_route("/", health_check_resource.on_get_home, methods=["GET"])
    application.add_api_route(
        "/health_check",
        health_check_resource.on_get_health_check,
        methods=["GET"],
    )

    customer_resource = CustomerResource()
    application.add_api_route("/customers", customer_resource.on_post, methods=["POST"])
    application.add_api_route("/customers/{customer_key}", customer_resource.on_get, methods=["GET"])
    application.add_api_route("/customers/{customer_key}/documents", customer_resource.on_post_document, methods=["POST"])
    application.add_api_route("/customers/{customer_key}/documents", customer_resource.on_get_documents, methods=["GET"])

    internal_resource = InternalCustomerResource()
    application.add_api_route("/internal/customers", internal_resource.on_get_by_contact, methods=["GET"])
    application.add_api_route("/internal/customers/{customer_key}", internal_resource.on_get, methods=["GET"])
    application.add_api_route("/internal/documents/{document_key}", internal_resource.on_get_document, methods=["GET"])

    register_error_handlers(application)

    return application


def main() -> FastAPI:
    check_variables()
    error_verification()
    setup_logging()

    return create_app()


app = main()
