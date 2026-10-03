# Casos de cancelamento pelo master (RFC):
# - master cancela conta pendente -> 200 e libera o master para abrir outra   [feito]
# - quem não é master tenta cancelar -> 422 QIT002028  [coberto pelo código do cancelamento]
# - conta já ativa não pode ser cancelada -> 409 QIT002026  [coberto pelo código do cancelamento]
# - conta inexistente -> 404 QIT002020  [coberto pelo código do cancelamento]
import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/account"


def _criar_conta(master, convidado):
    resposta = requests.post(
        ACCOUNT_URL,
        json={"customer_key": master["customer_key"], "name": "Apartamento 302", "invite_phones": [convidado["phone"]]},
        headers=HEADERS,
    )
    resposta.raise_for_status()
    return resposta.json()["account_key"]


def test_master_cancela_conta_pendente_e_fica_livre_para_abrir_outra():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)

    cancelamento = requests.put(f"{ACCOUNT_URL}/{account_key}/cancel",
                                json={"customer_key": master["customer_key"]}, headers=HEADERS)
    nova_conta = requests.post(
        ACCOUNT_URL,
        json={"customer_key": master["customer_key"], "name": "Casa nova", "invite_phones": [cadastrar_cliente()["phone"]]},
        headers=HEADERS,
    )

    assert cancelamento.status_code == 200
    assert nova_conta.status_code == 201


def test_quem_nao_e_master_nao_cancela_conta_devolve_422_qit002028():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)

    resposta = requests.put(f"{ACCOUNT_URL}/{account_key}/cancel",
                            json={"customer_key": convidado["customer_key"]}, headers=HEADERS)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002028"


def test_conta_ja_ativa_nao_pode_ser_cancelada_devolve_409_qit002026():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)
    holder_key = requests.get(f"{SERVICES['customer-service']}/customer/{convidado['customer_key']}/invitations",
                              headers=HEADERS).json()["data"][0]["holder_key"]
    requests.put(f"{SERVICES['account-service']}/invitation/{holder_key}/accept",
                 json={"customer_key": convidado["customer_key"]}, headers=HEADERS)

    resposta = requests.put(f"{ACCOUNT_URL}/{account_key}/cancel",
                            json={"customer_key": master["customer_key"]}, headers=HEADERS)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002026"


def test_conta_inexistente_devolve_404_qit002020():
    master = cadastrar_cliente()

    resposta = requests.put(f"{ACCOUNT_URL}/00000000-0000-0000-0000-000000000000/cancel",
                            json={"customer_key": master["customer_key"]}, headers=HEADERS)

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"
