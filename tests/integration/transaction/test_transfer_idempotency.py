import uuid

import requests

from utils.account_utils import criar_conta_ativa
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['transaction-service']}/account"


def _preparar():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    requests.post(
        f"{URL}/{origem['account_key']}/deposit",
        json={"customer_key": origem["master"]["customer_key"], "amount_cents": 20000},
        headers=HEADERS,
    ).raise_for_status()
    corpo = {
        "customer_key": origem["master"]["customer_key"],
        "amount_cents": 15000,
        "destination_account_number": destino["account_number"],
        "destination_document_number": destino["master"]["document_number"],
    }
    return origem, corpo


def _transferir(origem, corpo, chave):
    headers = dict(HEADERS)
    if chave is not None:
        headers["Idempotency-Key"] = chave
    return requests.post(f"{URL}/{origem['account_key']}/transfer", json=corpo, headers=headers)


def test_transferencia_sem_idempotency_key_devolve_400_qit000001():
    origem, corpo = _preparar()

    resposta = _transferir(origem, corpo, None)

    assert resposta.status_code == 400
    assert resposta.json()["code"] == "QIT000001"


def test_mesma_chave_e_mesmo_corpo_devolve_a_mesma_transacao_sem_debito_duplicado():
    origem, corpo = _preparar()
    chave = str(uuid.uuid4())

    primeira = _transferir(origem, corpo, chave)
    repetida = _transferir(origem, corpo, chave)

    assert primeira.status_code == 201
    assert repetida.status_code == 201
    assert repetida.json()["transaction_key"] == primeira.json()["transaction_key"]


def test_mesma_chave_com_corpo_diferente_devolve_422_qit002047():
    origem, corpo = _preparar()
    chave = str(uuid.uuid4())
    _transferir(origem, corpo, chave)

    resposta = _transferir(origem, {**corpo, "amount_cents": 1000}, chave)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002047"
