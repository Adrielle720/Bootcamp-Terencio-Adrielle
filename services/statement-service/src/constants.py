import os


SERVICE_ROOT = os.path.abspath(os.path.dirname(__file__))
SCHEMA_PATH = os.path.join(SERVICE_ROOT, "schemas")

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "bootcamp-api")

INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN")

ACCOUNT_SERVICE_URL = os.environ.get("ACCOUNT_SERVICE_URL", "http://localhost:8002")
TRANSACTION_SERVICE_URL = os.environ.get("TRANSACTION_SERVICE_URL", "http://localhost:8003")

# Toda chamada para outro serviço tem prazo. Sem prazo, um serviço lento prende este.
SERVICE_TIMEOUT = int(os.environ.get("SERVICE_TIMEOUT", "5"))

BYPASS_ENDPOINTS = [
    "/",
    "/health_check",
]

REQUIRED_VARIABLES = ["INTERNAL_TOKEN"]


def check_variables():
    missing = []
    for name in REQUIRED_VARIABLES:
        if not globals().get(name):
            missing.append(name)

    if missing:
        raise EnvironmentError(
            f"Faltam variáveis de ambiente: {', '.join(missing)}."
        )
