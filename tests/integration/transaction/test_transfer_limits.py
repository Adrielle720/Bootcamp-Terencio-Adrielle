import uuid

import requests

from utils.account_utils import criar_conta_ativa, criar_conta_com_titulares
from utils.settings import HEADERS, SERVICES

TRANSACTION_URL = f"{SERVICES['transaction-service']}/account"
ACCOUNT_URL = f"{SERVICES['account-service']}/account"


def _depositar(conta, valor):
    requests.post(
        f"{TRANSACTION_URL}/{conta['account_key']}/deposit",
        json={"customer_key": conta["master"]["customer_key"], "amount_cents": valor},
        headers=HEADERS,
    ).raise_for_status()


def _transferir(origem, destino, valor):
    return requests.post(
        f"{TRANSACTION_URL}/{origem['account_key']}/transfer",
        json={
            "customer_key": origem["master"]["customer_key"],
            "amount_cents": valor,
            "destination_account_number": destino["account_number"],
            "destination_document_number": destino["master"]["document_number"],
        },
        headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
    )


def test_transferencia_acima_do_limite_da_conta_devolve_422_qit002044():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    _depositar(origem, 1000000)

    definicao = requests.put(
        f"{ACCOUNT_URL}/{origem['account_key']}/transfer_limit",
        json={"customer_key": origem["master"]["customer_key"], "limit_cents": 10000},
        headers=HEADERS,
    )
    resposta = _transferir(origem, destino, 15000)

    assert definicao.status_code == 200
    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002044"
