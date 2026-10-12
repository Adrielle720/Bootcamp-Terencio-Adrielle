# Tarifa da transferência (RFC): base da faixa + máx(0, adultos ativos − 2) × R$ 0,50
# Faixas: 10,00–99,99 → 0,50 · 100,00–299,99 → 2,00 · 300,00–999,99 → 5,00 · 1.000,00–4.999,99 → 9,00 · ≥ 5.000,00 → 12,00
import pytest

from utils.account_utils import criar_conta_ativa, criar_conta_com_titulares, depositar, transferir


@pytest.mark.parametrize("valor, adultos, tarifa_esperada", [
    (1000, 2, 50),
    (9999, 2, 50),
    (10000, 2, 200),
    (25000, 3, 250),
    (29999, 2, 200),
    (30000, 2, 500),
    (50000, 2, 500),
    (99999, 2, 500),
    (100000, 2, 900),
    (200000, 4, 1000),
    (499999, 2, 900),
    (500000, 2, 1200),
    (600000, 6, 1400),
])
def test_tarifa_segue_faixa_e_adultos_ativos(valor, adultos, tarifa_esperada):
    origem = criar_conta_com_titulares(adultos)
    destino = criar_conta_ativa()
    depositar(origem, 1000000).raise_for_status()

    resposta = transferir(origem, destino, valor)

    assert resposta.status_code == 201
    assert resposta.json()["fee_cents"] == tarifa_esperada
    assert resposta.json()["total_cents"] == valor + tarifa_esperada
