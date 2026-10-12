# Limite por transferência da conta (RFC):
# - valor acima do limite -> 422 QIT002044
# - valor igual ao limite passa (o limite compara só o valor, sem a tarifa)
# - sem limite, só o saldo decide
import requests

from utils.account_utils import criar_conta_ativa, depositar, transferir
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/accounts"


def _definir_limite(conta, valor):
    requests.put(f"{ACCOUNT_URL}/{conta['account_key']}/transfer-limit",
                 json={"customer_key": conta["master"]["customer_key"], "limit_cents": valor},
                 headers=HEADERS).raise_for_status()


def test_transferencia_acima_do_limite_da_conta_devolve_422_qit002044():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 1000000).raise_for_status()
    _definir_limite(origem, 10000)

    resposta = transferir(origem, destino, 15000)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002044"


def test_transferencia_igual_ao_limite_passa():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 1000000).raise_for_status()
    _definir_limite(origem, 10000)

    resposta = transferir(origem, destino, 10000)

    assert resposta.status_code == 201


def test_limite_retirado_volta_a_aceitar_valores_altos():
    origem = criar_conta_ativa()
    destino = criar_conta_ativa()
    depositar(origem, 1000000).raise_for_status()
    _definir_limite(origem, 10000)
    _definir_limite(origem, None)

    resposta = transferir(origem, destino, 500000)

    assert resposta.status_code == 201
