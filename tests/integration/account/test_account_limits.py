# Casos de PUT /accounts/{account_key}/transfer-limit e PUT /account-holders/{key}/monthly-limit (RFC):
# - master define o limite por transferência -> 200; null tira o limite
# - membro que não é master -> 422 QIT002028
# - master define o limite mensal de um menor -> 200
# - titular que não é menor -> 422 QIT002029
# - titular inexistente -> 404 QIT002030
from datetime import date

import requests

from utils.account_utils import abrir_conta, aceitar_convite, consultar_conta, criar_conta_ativa
from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = SERVICES["account-service"]


def _limite_da_conta(conta, valor, quem=None):
    return requests.put(f"{ACCOUNT_URL}/accounts/{conta['account_key']}/transfer-limit",
                        json={"customer_key": (quem or conta["master"])["customer_key"], "limit_cents": valor},
                        headers=HEADERS)


def _limite_mensal(account_holder_key, quem, valor):
    return requests.put(f"{ACCOUNT_URL}/account-holders/{account_holder_key}/monthly-limit",
                        json={"customer_key": quem["customer_key"], "limit_cents": valor}, headers=HEADERS)


def _titular(conta_json, papel):
    return next(titular for titular in conta_json["holders"] if titular["role"] == papel)


def test_master_define_e_retira_o_limite_por_transferencia():
    conta = criar_conta_ativa()

    definicao = _limite_da_conta(conta, 10000)
    limite_definido = consultar_conta(conta["account_key"], conta["master"]).json()["transfer_limit_cents"]
    retirada = _limite_da_conta(conta, None)
    limite_retirado = consultar_conta(conta["account_key"], conta["master"]).json()["transfer_limit_cents"]

    assert definicao.status_code == 200
    assert limite_definido == 10000
    assert retirada.status_code == 200
    assert limite_retirado is None


def test_membro_nao_define_limite_da_conta_devolve_422_qit002028():
    conta = criar_conta_ativa()

    resposta = _limite_da_conta(conta, 10000, quem=conta["convidado"])

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002028"


def test_master_define_limite_mensal_do_menor():
    nascimento = date.today().replace(year=date.today().year - 16).isoformat()
    menor = cadastrar_cliente(birth_date=nascimento)
    adulto = cadastrar_cliente()
    master = cadastrar_cliente()
    account_key = abrir_conta(master, [{"phone": menor["phone"]}, {"phone": adulto["phone"]}]).json()["account_key"]
    aceitar_convite(adulto, account_key).raise_for_status()
    aceitar_convite(menor, account_key).raise_for_status()
    titular_menor = _titular(consultar_conta(account_key, master).json(), "MINOR")

    resposta = _limite_mensal(titular_menor["account_holder_key"], master, 20000)

    assert resposta.status_code == 200
    menor_depois = _titular(consultar_conta(account_key, master).json(), "MINOR")
    assert menor_depois["monthly_limit_cents"] == 20000


def test_limite_mensal_para_adulto_devolve_422_qit002029():
    conta = criar_conta_ativa()
    membro = _titular(consultar_conta(conta["account_key"], conta["master"]).json(), "MEMBER")

    resposta = _limite_mensal(membro["account_holder_key"], conta["master"], 20000)

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002029"


def test_limite_mensal_de_titular_inexistente_devolve_404_qit002030():
    resposta = _limite_mensal("00000000-0000-0000-0000-000000000000", cadastrar_cliente(), 20000)

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002030"
