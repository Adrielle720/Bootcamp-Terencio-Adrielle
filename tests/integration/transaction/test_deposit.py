# Casos da rota POST /account/{account_key}/deposit (RFC):
# - titular deposita em conta ativa -> 201 com transaction_key  [feito]
# - valor abaixo de R$ 10,00 -> 400 QIT000001  [regressão]
# - conta pendente, encerrada ou cancelada -> 409 QIT002026  [regressão: pendente]
# - conta inexistente ou quem pede não é titular ativo -> 404 QIT002020  [regressão: não titular]
import requests

from utils.account_utils import criar_conta_ativa
from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['transaction-service']}/account"


def test_titular_deposita_em_conta_ativa_e_recebe_201():
    conta = criar_conta_ativa()

    resposta = requests.post(
        f"{URL}/{conta['account_key']}/deposit",
        json={"customer_key": conta["master"]["customer_key"], "amount_cents": 50000},
        headers=HEADERS,
    )

    assert resposta.status_code == 201
    assert "transaction_key" in resposta.json()


def test_deposito_abaixo_de_10_reais_devolve_400_qit000001():
    conta = criar_conta_ativa()

    resposta = requests.post(
        f"{URL}/{conta['account_key']}/deposit",
        json={"customer_key": conta["master"]["customer_key"], "amount_cents": 999},
        headers=HEADERS,
    )

    assert resposta.status_code == 400
    assert resposta.json()["code"] == "QIT000001"


def test_deposito_em_conta_pendente_devolve_409_qit002026():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    conta = requests.post(
        f"{SERVICES['account-service']}/account",
        json={"customer_key": master["customer_key"], "name": "Apartamento 302", "invite_phones": [convidado["phone"]]},
        headers=HEADERS,
    ).json()

    resposta = requests.post(
        f"{URL}/{conta['account_key']}/deposit",
        json={"customer_key": master["customer_key"], "amount_cents": 50000},
        headers=HEADERS,
    )

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002026"


def test_quem_nao_e_titular_ativo_devolve_404_qit002020():
    conta = criar_conta_ativa()
    intruso = cadastrar_cliente()

    resposta = requests.post(
        f"{URL}/{conta['account_key']}/deposit",
        json={"customer_key": intruso["customer_key"], "amount_cents": 50000},
        headers=HEADERS,
    )

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002020"
