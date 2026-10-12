# Casos de PUT /accounts/{account_key}/cancel (RFC):
# - master cancela conta pendente -> 200 e fica livre para abrir outra
# - convidado que ainda não aceitou não é titular ativo -> 404 QIT002020 (R8)
# - conta já ativa não pode ser cancelada -> 409 QIT002026
# - conta inexistente -> 404 QIT002020
import requests

from utils.account_utils import abrir_conta, aceitar_convite, consultar_conta
from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/accounts"


def _cancelar(account_key, quem):
    return requests.put(f"{ACCOUNT_URL}/{account_key}/cancel",
                        json={"customer_key": quem["customer_key"]}, headers=HEADERS)


def test_master_cancela_conta_pendente_e_fica_livre_para_abrir_outra():
    master = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": cadastrar_cliente()["phone"]}]).json()["account_key"]

    cancelamento = _cancelar(account_key, master)
    nova_conta = abrir_conta(master, [{"phone": cadastrar_cliente()["phone"]}], nome="Casa nova")

    assert cancelamento.status_code == 200
    assert nova_conta.status_code == 201


def test_convidado_que_nao_aceitou_devolve_404_qit002020():
    convidado = cadastrar_cliente()
    account_key = abrir_conta(cadastrar_cliente(), [{"phone": convidado["phone"]}]).json()["account_key"]

    resposta = _cancelar(account_key, convidado)

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"


def test_conta_ja_ativa_nao_pode_ser_cancelada_devolve_409_qit002026():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": convidado["phone"]}]).json()["account_key"]
    aceitar_convite(convidado, account_key).raise_for_status()

    resposta = _cancelar(account_key, master)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002026"
    assert consultar_conta(account_key, master).json()["status"] == "ACTIVE"


def test_conta_inexistente_devolve_404_qit002020():
    resposta = _cancelar("00000000-0000-0000-0000-000000000000", cadastrar_cliente())

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"
