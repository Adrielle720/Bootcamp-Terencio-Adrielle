# Concorrência da transferência (RFC):
# - transferências simultâneas que juntas passam do saldo: exatamente uma aceita, nenhuma 500  [feito]
# - mesma chave simultânea: uma única transação, todas as respostas 201 com a mesma chave  [em andamento]
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests

from utils.account_utils import criar_conta_ativa
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['transaction-service']}/account"
SIMULTANEAS = 4


def _transferir(origem, destino):
    return requests.post(
        f"{URL}/{origem['account_key']}/transfer",
        json={
            "customer_key": origem["master"]["customer_key"],
            "amount_cents": 15000,
            "destination_account_number": destino["account_number"],
            "destination_document_number": destino["master"]["document_number"],
        },
        headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
    )


def test_transferencias_simultaneas_nao_passam_do_saldo_e_nunca_devolvem_500():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    requests.post(
        f"{URL}/{origem['account_key']}/deposit",
        json={"customer_key": origem["master"]["customer_key"], "amount_cents": 20000},
        headers=HEADERS,
    ).raise_for_status()

    with ThreadPoolExecutor(max_workers=SIMULTANEAS) as pool:
        respostas = list(pool.map(lambda _: _transferir(origem, destino), range(SIMULTANEAS)))

    codigos = sorted(resposta.status_code for resposta in respostas)
    assert codigos == [201] + [422] * (SIMULTANEAS - 1)


def test_mesma_chave_simultanea_gera_uma_unica_transacao():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    requests.post(
        f"{URL}/{origem['account_key']}/deposit",
        json={"customer_key": origem["master"]["customer_key"], "amount_cents": 50000},
        headers=HEADERS,
    ).raise_for_status()
    chave = str(uuid.uuid4())

    def _mesmo_pedido(_):
        return requests.post(
            f"{URL}/{origem['account_key']}/transfer",
            json={
                "customer_key": origem["master"]["customer_key"],
                "amount_cents": 15000,
                "destination_account_number": destino["account_number"],
                "destination_document_number": destino["master"]["document_number"],
            },
            headers={**HEADERS, "Idempotency-Key": chave},
        )

    with ThreadPoolExecutor(max_workers=SIMULTANEAS) as pool:
        respostas = list(pool.map(_mesmo_pedido, range(SIMULTANEAS)))

    assert all(resposta.status_code == 201 for resposta in respostas)
    assert len({resposta.json()["transaction_key"] for resposta in respostas}) == 1
