# Casos da rota POST /account (RFC):
# - master adulto abre conta pendente com convidados -> 201 com account_key e account_number  [em andamento]
# - master inexistente -> 404 QIT002010
# - master com menos de 18 anos -> 422 QIT002021  [em andamento]
# - master ou convidado já tem conta/convite -> 409 QIT002022  [em andamento]
# - telefone sem cliente -> 404 QIT002023  [em andamento]
# - convite a si mesmo ou repetido -> 422 QIT002024  [em andamento]
from datetime import date
import re

import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

URL = f"{SERVICES['account-service']}/account"
NUMERO_DA_CONTA = re.compile(r"^\d{8}-\d$")


def test_master_adulto_abre_conta_pendente_com_convidados():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()

    resposta = requests.post(
        URL,
        json={"customer_key": master["customer_key"], "name": "Apartamento 302", "invite_phones": [convidado["phone"]]},
        headers=HEADERS,
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert "account_key" in corpo
    assert NUMERO_DA_CONTA.match(corpo["account_number"])


def test_telefone_sem_cliente_devolve_404_qit002023():
    master = cadastrar_cliente()

    resposta = requests.post(
        URL,
        json={"customer_key": master["customer_key"], "name": "Apartamento 302", "invite_phones": ["11900000000"]},
        headers=HEADERS,
    )

    assert resposta.status_code == 404
    assert resposta.json()["code"] == "QIT002023"


def test_master_menor_de_18_anos_devolve_422_qit002021():
    nascimento = date.today().replace(year=date.today().year - 16).isoformat()
    master = cadastrar_cliente(birthdate=nascimento)
    convidado = cadastrar_cliente()

    resposta = requests.post(
        URL,
        json={"customer_key": master["customer_key"], "name": "Apartamento 302", "invite_phones": [convidado["phone"]]},
        headers=HEADERS,
    )

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002021"


def test_convidado_ja_convidado_em_outra_conta_devolve_409_qit002022():
    primeiro_master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    requests.post(
        URL,
        json={"customer_key": primeiro_master["customer_key"], "name": "Casa 1", "invite_phones": [convidado["phone"]]},
        headers=HEADERS,
    )
    segundo_master = cadastrar_cliente()

    resposta = requests.post(
        URL,
        json={"customer_key": segundo_master["customer_key"], "name": "Casa 2", "invite_phones": [convidado["phone"]]},
        headers=HEADERS,
    )

    assert resposta.status_code == 409
    assert resposta.json()["code"] == "QIT002022"


def test_master_convidando_a_si_mesmo_devolve_422_qit002024():
    master = cadastrar_cliente()

    resposta = requests.post(
        URL,
        json={"customer_key": master["customer_key"], "name": "Apartamento 302", "invite_phones": [master["phone"]]},
        headers=HEADERS,
    )

    assert resposta.status_code == 422
    assert resposta.json()["code"] == "QIT002024"
