# Casos de idempotência da transferência (RFC):
# - cabeçalho Idempotency-Key ausente -> 400 QIT000001
# - mesma chave e mesmo corpo -> 201 com a mesma transferência, sem débito duplicado
# - mesma chave e corpo diferente -> 422 QIT002047
import uuid

import requests

from utils.account_utils import consultar_conta, criar_conta_ativa, depositar, transferir
from utils.settings import HEADERS, SERVICES


def _preparar():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 20000).raise_for_status()
    return origem, destino


def test_transferencia_sem_idempotency_key_devolve_400_qit000001():
    origem, destino = _preparar()

    resposta = requests.post(
        f"{SERVICES['transaction-service']}/accounts/{origem['account_key']}/transfers",
        json={
            "customer_key": origem["master"]["customer_key"],
            "amount_cents": 15000,
            "destination_account_number": destino["account_number"],
            "destination_document_number": destino["master"]["document_number"],
        },
        headers=HEADERS,
    )

    assert resposta.status_code == 400
    assert resposta.json()["code"] == "QIT000001"


def test_mesma_chave_e_mesmo_corpo_devolve_a_mesma_transferencia_sem_debito_duplicado():
    origem, destino = _preparar()
    chave = str(uuid.uuid4())

    primeira = transferir(origem, destino, 15000, chave=chave)
    repetida = transferir(origem, destino, 15000, chave=chave)

    assert primeira.status_code == 201
    assert repetida.status_code == 201
    assert repetida.json() == primeira.json()
    assert consultar_conta(origem["account_key"], origem["master"]).json()["balance_cents"] == 20000 - 15200


def test_mesma_chave_com_corpo_diferente_devolve_422_qit002047():
    origem, destino = _preparar()
    chave = str(uuid.uuid4())
    transferir(origem, destino, 15000, chave=chave).raise_for_status()

    resposta = transferir(origem, destino, 1000, chave=chave)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002047"
