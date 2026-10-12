import os

from dotenv import load_dotenv

# O .env é opcional: sem ele, valem os mesmos padrões do docker-compose.yml.
load_dotenv()

SERVICES = {
    "customer-service": os.environ.get("CUSTOMER_URL", "http://localhost:8001"),
    "account-service": os.environ.get("ACCOUNT_URL", "http://localhost:8002"),
    "transaction-service": os.environ.get("TRANSACTION_URL", "http://localhost:8003"),
    "statement-service": os.environ.get("STATEMENT_URL", "http://localhost:8004"),
}

MOCKSERVER_URL = os.environ.get("MOCKSERVER_URL", "http://localhost:1080")

INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "default_token")
HEADERS = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
