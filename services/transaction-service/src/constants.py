import os


SERVICE_ROOT = os.path.abspath(os.path.dirname(__file__))
SCHEMA_PATH = os.path.join(SERVICE_ROOT, "schemas")

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "bootcamp-api")

DATABASE_URL = os.environ.get("DATABASE_URL")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN")

ACCOUNT_SERVICE_URL = os.environ.get("ACCOUNT_SERVICE_URL", "http://localhost:8002")

# Toda chamada para outro serviço tem prazo. Sem prazo, um serviço lento prende este.
SERVICE_TIMEOUT = int(os.environ.get("SERVICE_TIMEOUT", "5"))

# As duas contas da instituição, semeadas no database.sql. Elas só existem
# aqui: o account-service não as conhece, então nunca são destino.
FEE_REVENUE_ACCOUNT_KEY = os.environ.get("FEE_REVENUE_ACCOUNT_KEY", "00000000-0000-0000-0000-000000000001")
SETTLEMENT_ACCOUNT_KEY = os.environ.get("SETTLEMENT_ACCOUNT_KEY", "00000000-0000-0000-0000-000000000002")

BYPASS_ENDPOINTS = [
    "/",
    "/health_check",
]

REQUIRED_VARIABLES = ["DATABASE_URL", "INTERNAL_TOKEN"]


def check_variables():
    missing = []
    for name in REQUIRED_VARIABLES:
        if not globals().get(name):
            missing.append(name)

    if missing:
        raise EnvironmentError(
            f"Faltam variáveis de ambiente: {', '.join(missing)}."
        )
