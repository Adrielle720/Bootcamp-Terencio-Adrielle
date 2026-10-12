# Limite por transferência da conta (RFC):
# - valor acima do limite -> 422 QIT002044
# - valor igual ao limite passa (o limite compara só o valor, sem a tarifa)
# - sem limite, só o saldo decide
# - limite mensal do menor soma valor + tarifa do mês -> 422 QIT002045
# - menor sem limite mensal transfere até o saldo
import requests

from utils.account_utils import consultar_conta, criar_conta_ativa, depositar, transferir
from utils.minor_utils import aprovar_guarda_da_mae, conta_com_menor
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


def _limite_mensal(conta, valor):
    requests.put(f"{SERVICES['account-service']}/account-holders/{conta['menor']['holder_key']}/monthly-limit",
                 json={"customer_key": conta["master"]["customer_key"], "limit_cents": valor},
                 headers=HEADERS).raise_for_status()


def test_limite_mensal_do_menor_soma_valor_e_tarifa():
    conta = conta_com_menor()
    aprovar_guarda_da_mae(conta)
    destino = criar_conta_ativa()
    depositar(conta, 100000).raise_for_status()
    _limite_mensal(conta, 20000)

    primeira = transferir(conta, destino, 15000, quem=conta["menor"])
    segunda = transferir(conta, destino, 4800, quem=conta["menor"])
    dentro_do_limite = transferir(conta, destino, 4750, quem=conta["menor"])

    assert primeira.status_code == 201
    assert primeira.json()["total_cents"] == 15200
    assert segunda.status_code == 422
    assert segunda.json()["code"] == "QIT002045"
    assert dentro_do_limite.status_code == 201
    saldo = consultar_conta(conta["account_key"], conta["master"]).json()["balance_cents"]
    assert saldo == 100000 - 15200 - 4800


def test_menor_sem_limite_mensal_transfere_ate_o_saldo():
    conta = conta_com_menor()
    aprovar_guarda_da_mae(conta)
    depositar(conta, 100000).raise_for_status()

    resposta = transferir(conta, criar_conta_ativa(), 90000, quem=conta["menor"])

    assert resposta.status_code == 201
