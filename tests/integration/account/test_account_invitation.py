# Casos da rota POST /accounts/{account_key}/holders (RFC):
# - master convida mais alguém -> 201 com account_holder_key
# - sétima vaga -> 409 QIT002025
# - só o master convida -> 422 QIT002028
# - conta cancelada -> 409 QIT002026
# - convidado já participa de outra conta -> 409 QIT002022
# - conta inexistente -> 404 QIT002020
import requests

from utils.account_utils import abrir_conta, criar_conta_ativa
from utils.customer_utils import cadastrar_cliente
from utils.generators import gerar_telefone
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/accounts"


def _convidar(account_key, quem, contato):
    return requests.post(f"{ACCOUNT_URL}/{account_key}/holders",
                         json={"customer_key": quem["customer_key"], **contato}, headers=HEADERS)


def test_master_convida_mais_alguem_e_recebe_201():
    conta = criar_conta_ativa()

    resposta = _convidar(conta["account_key"], conta["master"], {"email": cadastrar_cliente()["email"]})

    assert resposta.status_code == 201
    assert "account_holder_key" in resposta.json()


def test_setima_vaga_devolve_409_qit002025():
    master = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": gerar_telefone()} for _ in range(5)]).json()["account_key"]

    resposta = _convidar(account_key, master, {"phone": gerar_telefone()})

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002025"


def test_membro_que_nao_e_master_devolve_422_qit002028():
    conta = criar_conta_ativa()

    resposta = _convidar(conta["account_key"], conta["convidado"], {"phone": gerar_telefone()})

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002028"


def test_conta_cancelada_devolve_409_qit002026():
    master = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": gerar_telefone()}]).json()["account_key"]
    requests.put(f"{ACCOUNT_URL}/{account_key}/cancel",
                 json={"customer_key": master["customer_key"]}, headers=HEADERS).raise_for_status()

    resposta = _convidar(account_key, master, {"phone": gerar_telefone()})

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002026"


def test_convidado_ja_em_outra_conta_devolve_409_qit002022():
    conta = criar_conta_ativa()
    outra = criar_conta_ativa()

    resposta = _convidar(conta["account_key"], conta["master"], {"phone": outra["convidado"]["phone"]})

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002022"


def test_conta_inexistente_devolve_404_qit002020():
    resposta = _convidar("00000000-0000-0000-0000-000000000000", cadastrar_cliente(), {"phone": gerar_telefone()})

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"
