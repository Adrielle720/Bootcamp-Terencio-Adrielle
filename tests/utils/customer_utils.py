import requests

from utils.generators import customer_payload
from utils.mock_utils import mock_bureau_ok
from utils.settings import HEADERS, SERVICES


def cadastrar_cliente(**sobrescrever) -> dict:
    payload = customer_payload(**sobrescrever)
    mock_bureau_ok(payload)

    resposta = requests.post(f"{SERVICES['customer-service']}/customer", json=payload, headers=HEADERS)
    resposta.raise_for_status()

    return {**payload, "customer_key": resposta.json()["customer_key"]}
