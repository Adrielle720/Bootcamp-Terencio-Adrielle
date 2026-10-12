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
from resources import AccountHolderResource, AccountResource, HealthCheckResource
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

    account_resource = AccountResource()
    application.add_api_route("/accounts", account_resource.on_post, methods=["POST"])
    application.add_api_route("/accounts/{account_key}", account_resource.on_get, methods=["GET"])
    application.add_api_route("/accounts/{account_key}/cancel", account_resource.on_put_cancel, methods=["PUT"])
    application.add_api_route("/accounts/{account_key}/block", account_resource.on_put_block, methods=["PUT"])
    application.add_api_route("/accounts/{account_key}/unblock", account_resource.on_put_unblock, methods=["PUT"])
    application.add_api_route("/accounts/{account_key}/transfer-limit", account_resource.on_put_transfer_limit, methods=["PUT"])

    holder_resource = AccountHolderResource()
    application.add_api_route("/accounts/{account_key}/holders", holder_resource.on_post, methods=["POST"])
    application.add_api_route("/account-holders", holder_resource.on_get_list, methods=["GET"])
    application.add_api_route("/account-holders/{account_holder_key}/accept", holder_resource.on_put_accept, methods=["PUT"])
    application.add_api_route("/account-holders/{account_holder_key}/decline", holder_resource.on_put_decline, methods=["PUT"])
    application.add_api_route("/account-holders/{account_holder_key}/cancel", holder_resource.on_put_cancel, methods=["PUT"])
    application.add_api_route("/account-holders/{account_holder_key}/monthly-limit", holder_resource.on_put_monthly_limit, methods=["PUT"])

    register_error_handlers(application)

    return application


def main() -> FastAPI:
    check_variables()
    error_verification()
    setup_logging()

    return create_app()


app = main()
