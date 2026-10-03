# Casos da rota POST /account (RFC):
# - master adulto abre conta pendente com convidados -> 201 com account_key e account_number  [em andamento]
# - master inexistente -> 404 QIT002010
# - master com menos de 18 anos -> 422 QIT002021
# - master ou convidado já tem conta/convite -> 409 QIT002022
# - telefone sem cliente -> 404 QIT002023  [em andamento]
# - convite a si mesmo ou repetido -> 422 QIT002024
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
