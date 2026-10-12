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
from resources import DepositResource, HealthCheckResource, InstitutionResource, TransferResource
from utils.logger import setup_logging


def create_app() -> FastAPI:
    application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    register_session_manager_middleware(application)
    register_internal_token_middleware(application)
    register_request_logger_middleware(application)
    register_request_context_middleware(application)

    health_check_resource = HealthCheckResource()
    application.add_api_route("/", health_check_resource.on_get_home, methods=["GET"])
    application.add_api_route("/health_check", health_check_resource.on_get_health_check, methods=["GET"])

    deposit_resource = DepositResource()
    application.add_api_route("/accounts/{account_key}/deposits", deposit_resource.on_post, methods=["POST"])

    transfer_resource = TransferResource()
    application.add_api_route("/accounts/{account_key}/transfers", transfer_resource.on_post, methods=["POST"])

    institution_resource = InstitutionResource()
    application.add_api_route("/internal/institution-balances", institution_resource.on_get_balances, methods=["GET"])

    register_error_handlers(application)

    return application


def main() -> FastAPI:
    check_variables()
    error_verification()
    setup_logging()

    return create_app()


app = main()
