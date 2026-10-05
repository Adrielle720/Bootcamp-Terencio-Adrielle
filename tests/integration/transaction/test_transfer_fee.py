# Tarifa da transferência (RFC): base da faixa + máx(0, adultos ativos − 2) × R$ 0,50
# Faixas: 10,00–99,99 → 0,50 · 100,00–299,99 → 2,00 · 300,00–999,99 → 5,00 · 1.000,00–4.999,99 → 9,00 · ≥ 5.000,00 → 12,00
import uuid

import pytest
import requests

from utils.account_utils import criar_conta_com_titulares, criar_conta_ativa
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['transaction-service']}/account"


def _depositar(conta, valor):
    requests.post(
        f"{URL}/{conta['account_key']}/deposit",
        json={"customer_key": conta["master"]["customer_key"], "amount_cents": valor},
        headers=HEADERS,
    ).raise_for_status()


@pytest.mark.parametrize("valor, adultos, tarifa_esperada", [
    (25000, 3, 250),
    (50000, 2, 500),
    (200000, 4, 1000),
    (600000, 6, 1400),
])
def test_tarifa_segue_faixa_e_adultos_ativos(valor, adultos, tarifa_esperada):
    origem = criar_conta_com_titulares(adultos)
    destino = criar_conta_ativa()
    _depositar(origem, 1000000)

    resposta = requests.post(
        f"{URL}/{origem['account_key']}/transfer",
        json={
            "customer_key": origem["master"]["customer_key"],
            "amount_cents": valor,
            "destination_account_number": destino["account_number"],
            "destination_document_number": destino["master"]["document_number"],
        },
        headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
    )

    assert resposta.status_code == 201
    assert resposta.json()["fee_cents"] == tarifa_esperada
    assert resposta.json()["total_cents"] == valor + tarifa_esperada
