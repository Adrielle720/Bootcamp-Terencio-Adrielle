# Casos de aceite, recusa e cancelamento de convite (RFC):
# - GET /customer/{key}/invitations lista os convites pendentes do cliente  [em andamento]
# - aceite do convite -> 200 e conta ativa
# - aceitar de novo -> 409 QIT002031
# - convite de outra pessoa -> 404 QIT002030
# - recusa do último convite de conta pendente cancela a conta e libera o master
import requests

from utils.customer_utils import cadastrar_cliente
from utils.settings import HEADERS, SERVICES

ACCOUNT_URL = f"{SERVICES['account-service']}/account"
CUSTOMER_URL = f"{SERVICES['customer-service']}/customer"


def _criar_conta(master, convidado):
    resposta = requests.post(
        ACCOUNT_URL,
        json={"customer_key": master["customer_key"], "name": "Apartamento 302", "invite_phones": [convidado["phone"]]},
        headers=HEADERS,
    )
    resposta.raise_for_status()
    return resposta.json()["account_key"]


def test_cliente_lista_seus_convites_pendentes():
    master = cadastrar_cliente()
    convidado = cadastrar_cliente()
    account_key = _criar_conta(master, convidado)

    resposta = requests.get(f"{CUSTOMER_URL}/{convidado['customer_key']}/invitations", headers=HEADERS)

    assert resposta.status_code == 200
    convites = resposta.json()["data"]
    assert len(convites) == 1
    assert convites[0]["account_key"] == account_key
    assert "holder_key" in convites[0]
