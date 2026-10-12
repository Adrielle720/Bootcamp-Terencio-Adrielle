# Casos de PUT /accounts/{account_key}/block e /unblock (RFC):
# - master bloqueia com justificativa -> 200; conta BLOCKED recebe dinheiro mas não envia
# - bloqueio sem justificativa -> 400 QIT000001
# - conta que não está ativa não é bloqueada -> 409 QIT002026
# - membro que não é master -> 422 QIT002028
# - master desbloqueia -> 200 e a conta volta a enviar; conta que não está bloqueada -> 409 QIT002026
import requests

from utils.account_utils import abrir_conta, consultar_conta, criar_conta_ativa, depositar, transferir
from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/accounts"


def _bloquear(conta, quem=None, motivo="Celular de um morador foi roubado"):
    corpo = {"customer_key": (quem or conta["master"])["customer_key"]}
    if motivo is not None:
        corpo["reason"] = motivo
    return requests.put(f"{ACCOUNT_URL}/{conta['account_key']}/block", json=corpo, headers=HEADERS)


def _desbloquear(conta, quem=None):
    return requests.put(f"{ACCOUNT_URL}/{conta['account_key']}/unblock",
                        json={"customer_key": (quem or conta["master"])["customer_key"]}, headers=HEADERS)


def test_conta_bloqueada_recebe_dinheiro_mas_nao_envia():
    conta = criar_conta_ativa()
    outra = criar_conta_ativa()
    depositar(conta, 50000).raise_for_status()
    depositar(outra, 50000).raise_for_status()

    bloqueio = _bloquear(conta)

    assert bloqueio.status_code == 200
    assert consultar_conta(conta["account_key"], conta["master"]).json()["status"] == "BLOCKED"
    assert depositar(conta, 1000).status_code == 201
    assert transferir(outra, conta, 1000).status_code == 201
    envio = transferir(conta, outra, 1000)
    assert envio.status_code == 409
    assert envio.json()["code"] == "QIT002026"


def test_bloqueio_sem_justificativa_devolve_400_qit000001():
    conta = criar_conta_ativa()

    resposta = _bloquear(conta, motivo=None)

    assert resposta.status_code == 400
    assert resposta.json()["code"] == "QIT000001"


def test_conta_pendente_nao_e_bloqueada_devolve_409_qit002026():
    master = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": cadastrar_cliente()["phone"]}]).json()["account_key"]

    resposta = _bloquear({"account_key": account_key, "master": master})

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002026"


def test_membro_que_nao_e_master_nao_bloqueia_devolve_422_qit002028():
    conta = criar_conta_ativa()

    resposta = _bloquear(conta, quem=conta["convidado"])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002028"


def test_master_desbloqueia_e_a_conta_volta_a_enviar():
    conta = criar_conta_ativa()
    outra = criar_conta_ativa()
    depositar(conta, 50000).raise_for_status()
    _bloquear(conta).raise_for_status()

    resposta = _desbloquear(conta)

    assert resposta.status_code == 200
    assert consultar_conta(conta["account_key"], conta["master"]).json()["status"] == "ACTIVE"
    assert transferir(conta, outra, 1000).status_code == 201


def test_desbloquear_conta_que_nao_esta_bloqueada_devolve_409_qit002026():
    conta = criar_conta_ativa()

    resposta = _desbloquear(conta)

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002026"
