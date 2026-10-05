# Casos da rota POST /account/{account_key}/transfer (RFC):
# - transferência entre contas ativas -> 201 com transaction_key  [em andamento]
# - (próximos, funcionalidades 6 a 8): tarifa, saldo, dígito verificador, idempotência
import uuid

import requests

from utils.account_utils import criar_conta_ativa
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['transaction-service']}/account"


def _depositar(conta, valor):
    requests.post(
        f"{URL}/{conta['account_key']}/deposit",
        json={"customer_key": conta["master"]["customer_key"], "amount_cents": valor},
        headers=HEADERS,
    ).raise_for_status()


def test_transferencia_entre_contas_ativas_devolve_201():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    _depositar(origem, 50000)

    resposta = requests.post(
        f"{URL}/{origem['account_key']}/transfer",
        json={
            "customer_key": origem["master"]["customer_key"],
            "amount_cents": 10000,
            "destination_account_number": destino["account_number"],
            "destination_document_number": destino["master"]["document_number"],
        },
        headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
    )

    assert resposta.status_code == 201
    assert "transaction_key" in resposta.json()


def test_transferencia_acima_do_saldo_devolve_422_qit002046():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    _depositar(origem, 20000)
    requests.post(
        f"{URL}/{origem['account_key']}/transfer",
        json={
            "customer_key": origem["master"]["customer_key"],
            "amount_cents": 15000,
            "destination_account_number": destino["account_number"],
            "destination_document_number": destino["master"]["document_number"],
        },
        headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
    ).raise_for_status()

    resposta = requests.post(
        f"{URL}/{origem['account_key']}/transfer",
        json={
            "customer_key": origem["master"]["customer_key"],
            "amount_cents": 5000,
            "destination_account_number": destino["account_number"],
            "destination_document_number": destino["master"]["document_number"],
        },
        headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
    )

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002046"
